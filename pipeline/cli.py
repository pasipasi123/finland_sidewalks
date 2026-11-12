"""Run with python -m pipeline.cli. No Overpass, server, or database service needed."""
import argparse
import csv
import gc
import hashlib
import json
import math
import sqlite3
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import osmium
from pyproj import Transformer
from shapely import from_wkb, from_wkt, transform as coordinate_transform, union_all, line_merge
from shapely.geometry import LineString, mapping, shape
from shapely.strtree import STRtree

from .rules import category, candidate_category, tag_rejection, walking_surface
from .corridor import filter_outer_paths,flat_lines,direction_runs
from .network import WalkingNetwork,NETWORK_POLICY
from .junctions import supported_corner_links,sidewalk_end_extensions,supported_missing_chains,merge_link_intervals,CORNER_POLICY
from .platforms import PLATFORM_SCHEMA,PLATFORM_POLICY,platform_polygon,platform_access_ways
from .metrics import METRICS_VERSION, PER_CAPITA, update_per_capita
from .tagged import TAGGED_POLICY, tagged_sidewalks

TO_METRES = Transformer.from_crs(4326, 3067, always_xy=True).transform
TO_LONLAT = Transformer.from_crs(3067, 4326, always_xy=True).transform
VERSION = '1.6.5'
FOOTWAY_GEOMETRY = {'max_distance_m':20, 'max_angle_degrees':20,
                    'min_run_m':15,'max_turn_degrees':45}

def transform(function, geometry):
    return coordinate_transform(geometry, function, interleaved=False)

def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    temp.replace(path)

def calculation_signature(meta, boundaries, population, distance, version=VERSION):
    return hashlib.sha256((json.dumps(meta,sort_keys=True)+Path(boundaries).read_text(encoding='utf-8')+Path(population).read_text(encoding='utf-8-sig')+str(distance)+version).encode()).hexdigest()

def prepare(args):
    target = Path(args.cache)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError('Välimuisti on jo olemassa. Käytä uutta tiedostonimeä uudelle OSM-otokselle.')
    db = sqlite3.connect(target)
    db.executescript('CREATE TABLE ways(id INTEGER PRIMARY KEY,tags TEXT,geom BLOB); CREATE VIRTUAL TABLE bounds USING rtree(id,minx,maxx,miny,maxy); CREATE TABLE metadata(value TEXT);')
    db.executescript(PLATFORM_SCHEMA)
    factory = osmium.geom.WKTFactory()
    boundaries = []

    class Handler(osmium.SimpleHandler):
        count = 0

        def way(self, way):
            tags = dict(way.tags)
            is_platform=tags.get('public_transport')=='platform' or tags.get('highway')=='platform'
            if not candidate_category(tags) and not is_platform:
                return
            try:
                geom = transform(TO_METRES, from_wkt(factory.create_linestring(way)))
            except (osmium.InvalidLocationError, RuntimeError):
                raise ValueError(f'OSM way {way.id}: puuttuvat solmut; käytä täydellistä PBF-otosta.')
            if geom.length == 0:
                return
            if is_platform:
                polygon=platform_polygon(tags,geom)
                if polygon is not None:
                    x1,y1,x2,y2=polygon.bounds
                    db.execute('INSERT INTO platforms VALUES (?,?,?)',(way.id,json.dumps(tags),polygon.wkb))
                    db.execute('INSERT INTO platform_bounds VALUES (?,?,?,?,?)',(way.id,x1,x2,y1,y2))
            if not candidate_category(tags):return
            x1,y1,x2,y2 = geom.bounds
            db.execute('INSERT INTO ways VALUES (?,?,?)', (way.id, json.dumps(tags), geom.wkb))
            db.execute('INSERT INTO bounds VALUES (?,?,?,?,?)', (way.id,x1,x2,y1,y2))
            self.count += 1
            if self.count % 20000 == 0:
                db.commit()
                print(f'{self.count:,} väylää', flush=True)

        def area(self, area):
            tags = dict(area.tags)
            code = tags.get('ref:FI', tags.get('ref', ''))
            if tags.get('boundary') != 'administrative' or tags.get('admin_level') != '8' or not (len(code) == 3 and code.isdigit()):
                return
            geom = from_wkt(factory.create_multipolygon(area))
            if not geom.is_valid:
                raise ValueError(f'Virheellinen kuntaraja {code}')
            boundaries.append({'type':'Feature','properties':{'code':code,'name':tags.get('name:fi',tags.get('name',code))},'geometry':mapping(geom)})

    # Disk-backed location index avoids keeping all Finnish OSM nodes in RAM.
    index = str(target.resolve()) + '.nodes'
    try:
        Handler().apply_file(args.pbf, locations=True, idx='sparse_file_array,'+index)
        with open(args.pbf,'rb') as source:
            checksum = hashlib.file_digest(source,'sha256').hexdigest()
        meta = {'osm_date':args.osm_date, 'source':Path(args.pbf).name, 'sha256':checksum, 'version':VERSION,'cache_selection_version':6}
        db.execute('INSERT INTO metadata VALUES (?)',(json.dumps(meta),))
        db.commit()
        dump(args.boundaries, {'type':'FeatureCollection','features':boundaries})
        print(f'Valmis: {len(boundaries)} kuntarajaa. Tarkista kuntakoodit ennen laskentaa.')
    except Exception:
        db.close()
        target.unlink(missing_ok=True)
        raise
    finally:
        db.close()
        gc.collect()  # Release Pyosmium's mapped node index before unlink on Windows.
        try:
            Path(index).unlink(missing_ok=True)
        except PermissionError:
            print(f'Solmuindeksi vapautuu prosessin päättyessä: {index}', flush=True)

def pieces(line, step=5):
    # Walk the vertices once; repeated substring calls scan long OSM ways many times.
    coords = list(line.coords)
    for start,end in zip(coords,coords[1:]):
        length = math.hypot(end[0]-start[0],end[1]-start[1])
        if not length:
            continue
        count = math.ceil(length/step)
        for i in range(count):
            yield LineString([(start[0]+(end[0]-start[0])*t/count,start[1]+(end[1]-start[1])*t/count) for t in (i,i+1)])

def level(tags):
    return (tags.get('layer','0'),tags.get('bridge','no'),tags.get('tunnel','no'))

def alignment(a,b):
    ax,ay = a.coords[-1][0]-a.coords[0][0],a.coords[-1][1]-a.coords[0][1]
    bx,by = b.coords[-1][0]-b.coords[0][0],b.coords[-1][1]-b.coords[0][1]
    norm = math.hypot(ax,ay)*math.hypot(bx,by)
    return abs((ax*bx+ay*by)/norm) if norm else 0

def measure(boundary, ways, distance=20, progress=None, rejections=None, corridor_exclusions=None,platforms=(),platform_exclusions=None,collect_audit=True):
    """5 m direction sampling; only exact intersected lengths are accumulated."""
    roads = []
    for oid,tags,geom in ways:
        if category(tags) == 'road':
            roads.extend((oid,tags,p) for p in pieces(geom,25))
    geometries = [r[2] for r in roads]
    tree = STRtree(geometries)
    if progress:
        progress(f'{len(roads):,} ajoradan osaa; erillisten väylien läheisyysvertailu alkaa')
    network=WalkingNetwork(ways,level,distance)
    platform_access=platform_access_ways(ways,platforms,network)
    if platform_exclusions is not None:platform_exclusions.update(platform_access)
    paths = []
    supports = []
    confirmed_spines=set()
    candidates = []
    stats = Counter()
    audit = []
    if rejections is None:
        rejections = {}
    for number,(oid,tags,geom) in enumerate(ways,1):
        if progress and number % 2000 == 0:
            progress(f'{number:,} / {len(ways):,} lähtöväylää käsitelty')
        if oid in platform_access:
            rejections[str(oid)]='pysakkilaiturin_yhteys'
            continue
        kind = category(tags)
        if kind is None:
            reason=tag_rejection(tags)
            rejections[str(oid)] = reason
            raw=candidate_category(tags)
            if reason in {'highway_path','ei_hyvaksytty_kova_pinta'} and raw in {'footway','segregated','shared','unknown'}:
                kind='blocker_only_footway' if raw=='footway' else 'blocker_only_route'
            else:
                continue
        if kind=='road':
            continue
        strict = kind in {'footway','blocker_only_footway'}
        if strict:
            network_reason=network.rejection(tags,geom)
            if network_reason:
                rejections[str(oid)]=network_reason
                continue
        match_distance = min(distance,FOOTWAY_GEOMETRY['max_distance_m']) if strict else distance
        angle = FOOTWAY_GEOMETRY['max_angle_degrees'] if strict else 30
        matched = []
        for part in pieces(geom):
            nearby = tree.query(part.buffer(match_distance))
            eligible = [int(i) for i in nearby if level(tags)==level(roads[int(i)][1]) and alignment(part,geometries[int(i)]) >= math.cos(math.radians(angle)) and part.distance(geometries[int(i)]) <= match_distance]
            if not eligible:
                continue
            coverage = None
            for i in eligible:
                buf = geometries[i].buffer(match_distance)
                coverage = buf if coverage is None else coverage.union(buf)
            clipped = part.intersection(coverage)
            if clipped.length <= 1e-6:
                continue
            matched.append(clipped)
        if not matched:
            rejections[str(oid)] = 'ei_kadunvarsiosumaa'
            continue
        if strict:
            merged = line_merge(union_all(matched))
            runs = [run for line in flat_lines(merged) for run in direction_runs(line,FOOTWAY_GEOMETRY['max_turn_degrees']) if run.length >= FOOTWAY_GEOMETRY['min_run_m']-1e-6]
            if not runs:
                rejections[str(oid)] = 'jyrkat_kaanteet_katkaisevat_jakson' if any(line.length>=FOOTWAY_GEOMETRY['min_run_m'] for line in flat_lines(merged)) else 'kadunvarsijakso_liian_lyhyt'
                continue
            matched = [part for run in runs for part in pieces(run)]
            if kind=='footway' and sum(part.length for part in matched)>=0.9*geom.length and any(network.distance(network.intersections,network.key(level(tags),p))<=25 for p in geom.coords):
                confirmed_spines.add(oid)
        for part in matched:
            candidates.append((oid,tags,kind,part))
    living=[]
    for oid,tags,geom in ways:
        if tags.get('highway')=='living_street':
            living.extend((oid,tags,part) for part in pieces(geom,25))
    if progress:
        progress(f'{len(candidates):,} ehdokasosaa; lähempien saman puolen jalankulkuväylien tarkistus alkaa')
    kept,removed=filter_outer_paths(candidates,roads+living,distance,level,alignment,progress,confirmed_ids=confirmed_spines)
    isolated=network.isolated_rejections(ways,kept,ignored_continuations=platform_access)
    kept=[row for row in kept if row[0] not in isolated]
    blocked_ids={row['osm_id'] for row in removed}
    grouped={}
    for oid,tags,kind,part in kept:
        grouped.setdefault(oid,{'tags':tags,'kind':kind,'parts':[]})['parts'].append(part)
    for row in removed:
        rejections[str(row['osm_id'])]=row['reason']
    rejections.update({str(oid):reason for oid,reason in isolated.items()})
    for oid,record in grouped.items():
        tags,kind,parts=record['tags'],record['kind'],record['parts']
        if kind.startswith('blocker_only'):
            continue
        if kind=='footway' and oid in blocked_ids:
            merged=line_merge(union_all(parts))
            parts=[part for line in flat_lines(merged) for run in direction_runs(line,FOOTWAY_GEOMETRY['max_turn_degrees']) if run.length>=FOOTWAY_GEOMETRY['min_run_m']-1e-6 for part in pieces(run)]
        counted=False
        for part in parts:
            clipped=part.intersection(boundary)
            if clipped.length<=1e-6:
                continue
            counted=True
            stats[kind]+=clipped.length
            if kind in {'footway','segregated'} and not walking_surface(tags):
                stats['assumed_asphalt']+=clipped.length
            paths.append((clipped,tags))
            if kind in {'footway','segregated'}:
                supports.append((oid,tags,part))
            if collect_audit:
                audit.append({'type':'Feature','properties':{'osm_id':oid,'category':kind,'length_m':round(clipped.length,3)},'geometry':mapping(transform(TO_LONLAT,clipped))})
        if counted:
            rejections.pop(str(oid),None)
        elif oid not in blocked_ids:
            rejections[str(oid)]='kunnan_ulkopuolella'
    # A corner can be shorter or less parallel than a street-side run. It must
    # connect an accepted sidewalk to another accepted sidewalk or a crossing.
    walking_ways=[row for row in ways if row[0] not in platform_access]
    links=supported_corner_links(walking_ways,supports,network,distance)
    links.extend(sidewalk_end_extensions(walking_ways,supports,network,distance))
    links.extend(supported_missing_chains(walking_ways,supports,network,distance))
    links=merge_link_intervals(ways,links)
    if links:
        link_ids={oid for oid,_,_ in links}
        junction_connections={(oid,bid) for oid,tags,geom in links for point in geom.coords
                              for bid in network.walking_ids.get(network.key(level(tags),point),set()) if bid!=oid}
        link_parts=[(oid,tags,'footway',part) for oid,tags,geom in links for part in pieces(geom)]
        kept_links,removed_links=filter_outer_paths([row for row in candidates if row[0] not in link_ids]+link_parts,roads+living,min(distance+CORNER_POLICY['extra_distance_m'],CORNER_POLICY['max_distance_m']),level,alignment,only_ids=link_ids,confirmed_ids=confirmed_spines,junction_connections=junction_connections)
        lengths=Counter()
        for oid,_,_,part in kept_links:lengths[oid]+=part.length
        expected=Counter()
        for oid,_,geom in links:expected[oid]+=geom.length
        whole={oid for oid in expected if abs(lengths[oid]-expected[oid])<0.01}
        for oid,tags,_,part in kept_links:
            if oid not in whole:continue
            part=part.intersection(boundary)
            if part.length<=1e-6:continue
            stats['footway']+=part.length
            if not walking_surface(tags):stats['assumed_asphalt']+=part.length
            paths.append((part,tags))
            if collect_audit:
                audit.append({'type':'Feature','properties':{'osm_id':oid,'category':'footway','length_m':round(part.length,3),'junction_link':True},'geometry':mapping(transform(TO_LONLAT,part))})
            rejections.pop(str(oid),None)
        removed.extend(removed_links)
    if corridor_exclusions is not None:
        corridor_exclusions.extend(removed)
    # A separately mapped qualifying path takes precedence over the same road side.
    if progress:
        progress(f'{len(paths):,} hyväksyttyä erillisväylän osaa; ajoratatägien kaksoislaskennan poisto alkaa')
    for oid,side,remaining in tagged_sidewalks([row for row in ways if category(row[1])=='road'],paths,boundary,distance,level):
        stats['tagged'] += remaining.length
        if collect_audit:
            audit.append({'type':'Feature','properties':{'osm_id':oid,'category':'tagged','side':side,'length_m':round(remaining.length,3)},'geometry':mapping(transform(TO_LONLAT,remaining))})
    return stats,audit

def compute(args):
    features = json.loads(Path(args.boundaries).read_text(encoding='utf-8'))['features']
    codes = {x.strip().zfill(3) for x in args.codes.split(',')} if args.codes else None
    with open(args.population,encoding='utf-8-sig',newline='') as file:
        population = {row['code'].zfill(3):row for row in csv.DictReader(file)}
    db = sqlite3.connect(f'file:{Path(args.cache).resolve().as_posix()}?mode=ro', uri=True)
    metadata_row = db.execute('SELECT value FROM metadata').fetchone()
    if metadata_row is None:
        db.close()
        raise ValueError('OSM-välimuistin valmistelu ei ole valmistunut. Tee prepare uuteen tiedostoon.')
    meta = json.loads(metadata_row[0])
    if meta.get('cache_selection_version',1)<6:
        db.close()
        raise ValueError('Vanha välimuistin valinta: aja tarvittavat scripts.extend_reference_roads, scripts.extend_walking_candidates, scripts.extend_crossing_context, scripts.extend_bus_references ja scripts.extend_platform_context moduuleina tai valmistele uusi välimuisti.')
    selected = [f for f in features if codes is None or f['properties']['code'] in codes]
    if codes and codes - {f['properties']['code'] for f in selected}:
        raise ValueError('Kuntakoodia ei löydy raja-aineistosta.')
    signature = calculation_signature(meta,args.boundaries,args.population,args.distance)
    for feature in selected:
        started = time.perf_counter()
        code = feature['properties']['code']
        output = Path(args.output)/f'{code}.json'
        if output.exists() and not args.force:
            existing = json.loads(output.read_text(encoding='utf-8'))
            if existing.get('signature') == signature:
                if update_per_capita(existing):
                    dump(output, existing)
                print(f'{code}: geometriat ennallaan, asukasmittarit ajan tasalla')
                continue
        pop = population[code]
        n = int(pop['population'])
        if n <= 0 or not pop['date'] or not pop['source']:
            raise ValueError(f'{code}: väestömäärä, päiväys ja lähde vaaditaan')
        boundary = transform(TO_METRES,shape(feature['geometry']))
        if not boundary.is_valid:
            raise ValueError(f'{code}: virheellinen kuntaraja')
        x1,y1,x2,y2 = boundary.buffer(args.distance+10).bounds
        rows = db.execute('SELECT w.id,w.tags,w.geom FROM ways w JOIN bounds b ON w.id=b.id WHERE b.maxx>=? AND b.minx<=? AND b.maxy>=? AND b.miny<=?',(x1,x2,y1,y2))
        ways = [(oid,json.loads(tags),from_wkb(geom)) for oid,tags,geom in rows]
        platform_rows=db.execute('SELECT p.id,p.tags,p.geom FROM platforms p JOIN platform_bounds b ON p.id=b.id WHERE b.maxx>=? AND b.minx<=? AND b.maxy>=? AND b.miny<=?',(x1,x2,y1,y2))
        platforms=[(oid,json.loads(tags),from_wkb(geom)) for oid,tags,geom in platform_rows]
        print(f'{code}: {len(ways):,} lähtöväylää kunnan rajauslaatikossa',flush=True)
        rejections = {}
        corridor_exclusions=[]
        platform_exclusions={}
        summary_only = getattr(args,'summary_only',False)
        stats,audit = measure(boundary, ways,args.distance,progress=lambda message:print(f'{code}: {message}',flush=True),rejections=rejections,corridor_exclusions=None if summary_only else corridor_exclusions,platforms=platforms,platform_exclusions=platform_exclusions,collect_audit=not summary_only)
        km = {k:round(stats[k]/1000,6) for k in ('tagged','footway','segregated','shared','unknown')}
        total = sum(km[k] for k in ('tagged','footway','segregated'))
        result = {'code':code,'name':feature['properties']['name'],'population':n,'population_date':pop['date'],'population_source':pop['source'],'km':km,'total_km':round(total,6),'m_per_resident':round(total*1000/n,4),'geometry':feature['geometry'],'osm':meta,'distance_m':args.distance,'signature':signature,'method_version':VERSION,'generated_at':datetime.now(timezone.utc).isoformat()}
        update_per_capita(result)
        result['diagnostics'] = {'input_ways':len(ways), 'audit_features':None if summary_only else len(audit), 'detail_geometry_exported':not summary_only, 'calculation_seconds':round(time.perf_counter()-started,3)}
        result['footway_geometry'] = FOOTWAY_GEOMETRY
        result['network_policy'] = NETWORK_POLICY
        result['corner_link_policy'] = CORNER_POLICY
        result['platform_policy'] = PLATFORM_POLICY
        result['surface_policy'] = {'missing':'assumed_asphalt','known_non_hard':'excluded'}
        result['tagged_policy'] = TAGGED_POLICY
        result['corridor_policy'] = {'innermost_walking_route_only':True,'side_order_tolerance_m':0.25,'living_street_included':False,
                                     'road_sidewalk_no_blocks_inference':True,'explicit_sidepath_overrides_road_no':True}
        result['assumed_asphalt_km'] = round(stats['assumed_asphalt']/1000,6)
        result['diagnostics']['rejected_way_counts'] = dict(Counter(rejections.values()))
        exclusion_info={}
        exclusion_features=[]
        for row in corridor_exclusions:
            geom=row['geometry'].intersection(boundary)
            if geom.length<=1e-6:
                continue
            info=exclusion_info.setdefault(str(row['osm_id']),{'removed_m':0,'blockers':set(),'road_ids':set(),'reason':row['reason']})
            info['removed_m']+=geom.length
            info['blockers'].update(row['blockers'])
            info['road_ids'].add(row['road_id'])
            exclusion_features.append({'type':'Feature','geometry':mapping(transform(TO_LONLAT,geom)),'properties':{k:v for k,v in row.items() if k!='geometry'}|{'length_m':round(geom.length,3)}})
        for info in exclusion_info.values():
            info['blockers']=sorted(info['blockers']);info['road_ids']=sorted(info['road_ids']);info['removed_m']=round(info['removed_m'],3)
        if not summary_only:
            result['diagnostics']['corridor_removed_m']=round(sum(v['removed_m'] for v in exclusion_info.values()),3)
        dump(output,result)
        if summary_only:
            print(f'{code} {result["name"]}: {total:.3f} km (vain kuntayhteenveto)',flush=True)
            continue
        dump(Path(args.output)/f'{code}.segments.geojson',{'type':'FeatureCollection','features':audit})
        dump(Path(args.output)/f'{code}.rejections.json',{'signature':signature,'ways':rejections,'corridor_exclusions':exclusion_info,'platform_access':platform_exclusions})
        dump(Path(args.output)/f'{code}.platforms.geojson',{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'osm_id':oid,**tags},'geometry':mapping(transform(TO_LONLAT,area))} for oid,tags,area in platforms]})
        dump(Path(args.output)/f'{code}.corridor_exclusions.geojson',{'type':'FeatureCollection','features':exclusion_features})
        print(f'{code} {result["name"]}: {total:.3f} km',flush=True)
    db.close()

def svg_path(geometry):
    poly = transform(TO_METRES,shape(geometry))
    polygons = [poly] if poly.geom_type=='Polygon' else list(poly.geoms)
    return ' '.join('M'+' L'.join(f'{x/1000:.3f},{-y/1000:.3f}' for x,y in ring.coords)+' Z' for polygon in polygons for ring in [polygon.exterior,*polygon.interiors])

def publish(args):
    rows = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(Path(args.results).glob('[0-9][0-9][0-9].json'))]
    if not rows:
        raise ValueError('Laskettuja kuntia ei löydy')
    if getattr(args,'expected_count',None) is not None and len(rows)!=args.expected_count:
        raise ValueError(f'Kattavuus on {len(rows)}, odotettiin {args.expected_count}. Osittaista aineistoa ei julkaista.')
    if len({(r['signature']) for r in rows}) != 1:
        raise ValueError('Tuloksissa eri OSM-, väestö-, raja- tai menetelmäversioita. Laske yhtenäisillä lähtötiedoilla.')
    if {r['method_version'] for r in rows}!={VERSION}:
        raise ValueError('Kuntatulosten menetelmä ei vastaa nykyistä laskentaversiota. Laske tulokset uudelleen.')
    for row in rows:
        update_per_capita(row)
    names_from = getattr(args,'names_from',None)
    if names_from:
        raw = json.loads(Path(names_from).read_text(encoding='utf-8'))
        labels = next(d['category']['label'] for d in raw['response']['dimension'].values() if any(k.startswith('KU') for k in d.get('category',{}).get('label',{})))
        for row in rows:
            label=labels['KU'+row['code']]
            if label!=row['name']:
                row['name_aliases']=[label]
    for metric in ('total_km','m_per_resident', *PER_CAPITA):
        for rank,row in enumerate(sorted(rows,key=lambda r:r[metric],reverse=True),1):
            row['rank_'+metric] = rank
    table_only = getattr(args,'table_only',False)
    metadata = {'demo':False,'coverage_count':len(rows),'method_version':VERSION,'metrics_version':METRICS_VERSION,'license':'ODbL-1.0','population_license':'CC-BY-4.0'}
    if getattr(args,'expected_count',None) is not None:
        metadata['expected_count']=args.expected_count
    csv_rows=rows
    if table_only:
        if len({(r['population_date'],r['population_source'],r['distance_m']) for r in rows})!=1:
            raise ValueError('Tiivis taulukko vaatii yhteisen väestöpäivän, lähteen ja etäisyysrajan')
        metadata.update(osm=rows[0]['osm'],population_date=rows[0]['population_date'],population_source=rows[0]['population_source'],distance_m=rows[0]['distance_m'],signature=rows[0]['signature'],generated_at=datetime.now(timezone.utc).isoformat())
        fields = {'code','name','name_aliases','population','km','total_km','m_per_resident',*PER_CAPITA}
        rows = [{k:v for k,v in row.items() if k in fields or k.startswith('rank_')} for row in rows]
    else:
        for row in rows:
            row['map_path'] = svg_path(row['geometry'])
            del row['geometry']
    dump(args.output,{**metadata,'municipalities':rows})
    csv_output=getattr(args,'csv_output',None)
    if csv_output:
        target=Path(csv_output)
        target.parent.mkdir(parents=True,exist_ok=True)
        fields=['code','name','population','sidewalks_km','sidewalks_m_per_resident','shared_km','shared_m_per_resident','segregated_km','segregated_m_per_resident','unknown_km','unknown_m_per_resident','tagged_km','footway_km','osm_date','population_date','population_source','method_version']
        with target.open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields)
            writer.writeheader()
            for row in csv_rows:
                record={k:row[k] for k in ['code','name','population','shared_m_per_resident','segregated_m_per_resident','unknown_m_per_resident','population_date','population_source','method_version']}
                record.update(sidewalks_km=row['total_km'],sidewalks_m_per_resident=row['m_per_resident'],osm_date=row['osm']['osm_date'])
                record.update({k+'_km':row['km'][k] for k in ['shared','segregated','unknown','tagged','footway']})
                writer.writerow(record)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    prep = sub.add_parser('prepare'); prep.add_argument('--pbf',required=True); prep.add_argument('--osm-date',required=True); prep.add_argument('--cache',default='data/cache/finland.db'); prep.add_argument('--boundaries',default='data/cache/municipalities.geojson'); prep.set_defaults(run=prepare)
    calc = sub.add_parser('compute'); calc.add_argument('--codes',help='Esim. 564,091; ilman valintaa kaikki kunnat'); calc.add_argument('--cache',default='data/cache/finland.db'); calc.add_argument('--boundaries',default='data/cache/municipalities.geojson'); calc.add_argument('--population',required=True); calc.add_argument('--distance',type=float,default=20); calc.add_argument('--output',default='data/results'); calc.add_argument('--force',action='store_true'); calc.set_defaults(run=compute)
    calc.add_argument('--summary-only',action='store_true',help='Vain kuntatulos; ei uusia katselu- tai auditointigeometrioita')
    pub = sub.add_parser('publish'); pub.add_argument('--results',default='data/results/national'); pub.add_argument('--output',default='web/data/municipalities.json'); pub.set_defaults(run=publish)
    pub.add_argument('--table-only',action='store_true',default=True,help='Tiivis taulukkoaineisto ilman geometrioita (oletus)')
    pub.add_argument('--with-map',dest='table_only',action='store_false',help='Laaja kooste ja SVG-karttapolut erilliseen jatkokäyttöön')
    pub.add_argument('--expected-count',type=int,default=308,help='Vaadittu kuntamäärä (oletus 308); estää keskeneräisen ajon julkaisun')
    pub.add_argument('--csv-output',help='Vie rinnalle CSV-taulukko')
    pub.add_argument('--names-from',help='Väestöhaun raakavastaus kuntanimien hakualiasnimille')
    args = parser.parse_args()
    if args.command=='publish' and args.table_only and not args.csv_output:
        args.csv_output=str(Path(args.output).with_suffix('.csv'))
    if hasattr(args,'distance') and not 0 < args.distance <= 100:
        parser.error('Etäisyyden tulee olla 0–100 metriä')
    args.run(args)

if __name__ == '__main__':
    main()
