"""Export a computed municipality and its cached source ways for GIS inspection."""
import argparse
import json
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import fiona
from shapely import from_wkb
from shapely.geometry import MultiLineString, MultiPolygon, mapping, shape

from .cli import TO_METRES, transform
from .rules import candidate_category, tag_rejection, walking_surface

LAYERS = {
    'tagged': ('jalkakaytavat_ajoratatagit', 'Ajoradan sidewalk-tägi; geometria on ajoradan keskilinja, ei jalkakäytävän tarkka sijainti.'),
    'footway': ('jalkakaytavat_erilliset', 'Kadunvarsisuodatuksen hyväksymät erilliset jalankulkuväylien osuudet.'),
    'segregated': ('jalkakaytavat_erotellut', 'Kadunvarsisuodatuksen hyväksymä pyörätiestä eroteltu jalankulku.'),
    'shared': ('yhdistetyt_poissuljettu', 'Kadunvarren yhdistetty jalankulku ja pyöräily; EI sisälly jalkakäytäväsummaan.'),
    'unknown': ('erottelu_tuntematon', 'Kadunvarren pyörätie, jonka erottelutieto on tuntematon; EI sisälly jalkakäytäväsummaan.'),
}
INCLUDED = {'tagged', 'footway', 'segregated'}
TAG_FIELDS = {
    'nimi': 'name', 'highway': 'highway', 'footway': 'footway', 'foot': 'foot',
    'bicycle': 'bicycle', 'segregated': 'segregated', 'sidewalk': 'sidewalk',
    'sidewalk_left': 'sidewalk:left', 'sidewalk_right': 'sidewalk:right',
    'sidewalk_both': 'sidewalk:both', 'access': 'access', 'layer': 'layer',
    'bridge': 'bridge', 'tunnel': 'tunnel',
    'surface': 'surface', 'footway_surface': 'footway:surface',
}
COMMON = {'osm_id': 'int64', **{key: 'str' for key in TAG_FIELDS}, 'tags_json': 'str', 'osm_url': 'str', 'pinnan_tila':'str','laskenta_pinta':'str'}


def line_geometry(geometry):
    """Normalize multipart intersections and discard any zero-length touch points."""
    if geometry.is_empty:
        return None
    if geometry.geom_type == 'LineString':
        return MultiLineString([geometry]) if geometry.length else None
    if geometry.geom_type == 'MultiLineString':
        lines = [member for member in geometry.geoms if member.length]
        return MultiLineString(lines) if lines else None
    if geometry.geom_type == 'GeometryCollection':
        lines = []
        for member in geometry.geoms:
            normalized = line_geometry(member)
            if normalized is not None:
                lines.extend(normalized.geoms)
        return MultiLineString(lines) if lines else None
    return None


def properties(osm_id, tags):
    road = tags.get('highway') not in {'footway','cycleway','path'}
    surface = walking_surface(tags)
    return {'osm_id': osm_id, **{key: tags.get(tag) for key,tag in TAG_FIELDS.items()},
            'tags_json': json.dumps(tags, ensure_ascii=False, sort_keys=True),
            'osm_url': f'https://www.openstreetmap.org/way/{osm_id}',
            'pinnan_tila':'ei_sovelleta' if road else ('osm_tieto' if surface else 'oletus_asfaltti'),
            'laskenta_pinta':None if road else (surface or 'asphalt')}


def write_layer(path, name, schema, records, description):
    count = 0

    def counted():
        nonlocal count
        for record in records:
            count += 1
            yield record

    with fiona.open(path, 'w', driver='GPKG', layer=name, schema=schema,
                    crs='EPSG:3067', encoding='UTF-8', SPATIAL_INDEX='YES',
                    DESCRIPTION=description) as sink:
        sink.writerecords(counted())
    print(f'{name}: {count:,} kohdetta', flush=True)
    return count


def export_gpkg(result_path, audit_path, cache_path, output_path):
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.stem + '.building.gpkg')
    if target.exists() or partial.exists():
        raise ValueError(f'Tulos tai keskeneräinen vienti on jo olemassa: {target}. Valitse uusi tiedostonimi.')
    result = json.loads(Path(result_path).read_text(encoding='utf-8'))
    audit = json.loads(Path(audit_path).read_text(encoding='utf-8'))['features']
    rejection_path = Path(result_path).with_suffix('.rejections.json')
    rejections = {}
    corridor_exclusions = {}
    if rejection_path.exists():
        rejection_data = json.loads(rejection_path.read_text(encoding='utf-8'))
        if rejection_data['signature'] != result['signature']:
            raise ValueError('Hylkäystiedot eivät vastaa laskentatulosta.')
        rejections = rejection_data['ways']
        corridor_exclusions = rejection_data.get('corridor_exclusions',{})
    boundary = transform(TO_METRES, shape(result['geometry']))
    if not boundary.is_valid:
        raise ValueError('Virheellinen kuntageometria')
    context_area = boundary.buffer(result['distance_m'] + 10)
    x1,y1,x2,y2 = context_area.bounds
    with closing(sqlite3.connect(f'file:{Path(cache_path).resolve().as_posix()}?mode=ro', uri=True)) as db:
        metadata = json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
        if metadata != result['osm']:
            raise ValueError('Välimuisti ei vastaa laskennassa käytettyä OSM-otosta.')
        rows = db.execute('SELECT w.id,w.tags,w.geom FROM ways w JOIN bounds b ON w.id=b.id WHERE b.maxx>=? AND b.minx<=? AND b.maxy>=? AND b.miny<=? ORDER BY w.id', (x1,x2,y1,y2))
        ways = {oid:(json.loads(tags),geom) for oid,tags,geom in rows}
    sums = Counter()
    counts = Counter()
    per_way = Counter()
    included_per_way = Counter()
    for feature in audit:
        props = feature['properties']
        kind = props['category']
        osm_id = props['osm_id']
        if kind not in LAYERS or osm_id not in ways:
            raise ValueError('Auditointiaineisto ei vastaa lähtöväyliä.')
        sums[kind] += props['length_m']
        counts[kind] += 1
        per_way[osm_id] += props['length_m']
        if kind in INCLUDED:
            included_per_way[osm_id] += props['length_m']
    for kind in LAYERS:
        if abs(sums[kind] - result['km'][kind]*1000) > max(1,counts[kind]*0.00051):
            raise ValueError(f'Auditoinnin pituussumma ei vastaa tulosta: {kind}')

    manifest = {}
    omitted_zero_length = Counter()
    try:
        for kind,(name,description) in LAYERS.items():
            def records(kind=kind):
                for feature in audit:
                    props = feature['properties']
                    if props['category'] != kind:
                        continue
                    geometry = line_geometry(transform(TO_METRES,shape(feature['geometry'])))
                    if geometry is None:
                        if props['length_m'] == 0:
                            omitted_zero_length[kind] += 1
                            continue
                        raise ValueError('Auditoinnista löytyi kohde ilman viivageometriaa.')
                    yield {'geometry':mapping(geometry), 'properties':{
                        **properties(props['osm_id'], ways[props['osm_id']][0]),
                        'luokka':kind, 'mukana':int(kind in INCLUDED),
                        'pituus_m':props['length_m'], 'puoli':props.get('side'),
                        'geom_rooli':'ajoradan keskilinja' if kind=='tagged' else 'erillisen vaylan geometria'}}
            schema = {'geometry':'MultiLineString', 'properties':{**COMMON,'luokka':'str','mukana':'int','pituus_m':'float','puoli':'str','geom_rooli':'str'}}
            manifest[name] = write_layer(str(partial),name,schema,records(),description)

        for road_layer in (True,False):
            name = 'osm_ajoradat' if road_layer else 'osm_jalankulku_pyora'
            def source_records(road_layer=road_layer):
                for oid,(tags,wkb) in ways.items():
                    kind = candidate_category(tags)
                    if (tags.get('highway') not in {'footway','cycleway','path'}) != road_layer:
                        continue
                    geometry = line_geometry(from_wkb(wkb).intersection(context_area))
                    if geometry is None:
                        continue
                    yield {'geometry':mapping(geometry), 'properties':{
                        **properties(oid,tags),'luokka':kind,'naytettava_m':geometry.length,
                        'kadunvarsi_m':per_way[oid], 'mukaan_m':included_per_way[oid],
                        'audit_osumia':int(per_way[oid] > 0),
                        'hylkayssyy':tag_rejection(tags) or rejections.get(str(oid)) or (('osittain_'+corridor_exclusions[str(oid)]['reason']) if str(oid) in corridor_exclusions else None) or ({'shared':'yhdistetty_vayla','unknown':'erottelu_tuntematon'}.get(kind)),
                        'varjossa_m':corridor_exclusions.get(str(oid),{}).get('removed_m',0),
                        'estaja_osm':','.join(str(i) for i in corridor_exclusions.get(str(oid),{}).get('blockers',[])),
                        'viitekatu_osm':','.join(str(i) for i in corridor_exclusions.get(str(oid),{}).get('road_ids',[]))}}
            description = ('Laskennan välimuistin alkuperäiset ajoradat' if road_layer else 'Laskennan välimuistin alkuperäiset jalankulku- ja pyöräväylät') + f'; leikattu kuntarajaan + {result["distance_m"]+10:g} m puskuriin. Sisältää myös kadunvarsisuodatuksessa hylättyjä osia. Ei kaikkia OSM:n highway-luokkia.'
            schema = {'geometry':'MultiLineString', 'properties':{**COMMON,'luokka':'str','naytettava_m':'float','kadunvarsi_m':'float','mukaan_m':'float','audit_osumia':'int','hylkayssyy':'str','varjossa_m':'float','estaja_osm':'str','viitekatu_osm':'str'}}
            manifest[name] = write_layer(str(partial),name,schema,source_records(),description)

        polygon = MultiPolygon([boundary]) if boundary.geom_type=='Polygon' else boundary
        manifest['kuntaraja'] = write_layer(str(partial),'kuntaraja',
            {'geometry':'MultiPolygon','properties':{'koodi':'str','nimi':'str','jalkakaytavat_km':'float','m_asukas':'float','asukasluku':'int64'}},
            [{'geometry':mapping(polygon),'properties':{'koodi':result['code'],'nimi':result['name'],'jalkakaytavat_km':result['total_km'],'m_asukas':result['m_per_resident'],'asukasluku':result['population']}}],
            'Laskennassa käytetty OSM-kuntaraja. Ei virallinen kuntaraja-aineisto.')

        info = {
            'kunta':result['name'], 'kuntakoodi':result['code'], 'crs':'EPSG:3067',
            'luotu_utc':datetime.now(timezone.utc).isoformat(),
            'laskentatulos':json.dumps({k:v for k,v in result.items() if k!='geometry'},ensure_ascii=False),
            'tasojen_kohdemaarat':json.dumps(manifest,ensure_ascii=False),
            'ohitetut_nollageometriat':json.dumps(omitted_zero_length,ensure_ascii=False),
            'tulostasot':'Kolme jalkakaytavat_* -tasoa sisältyvät summaan. Yhdistetyt ja erottelu_tuntematon eivät sisälly.',
            'ajoratatagit':'Geometria on ajoradan keskilinja. puoli=left/right kertoo OSM-viivan suuntaan sidotun puolen; se ei ole jalkakäytävän tarkka sijainti. Molemmat puolet voivat olla päällekkäin.',
            'pituus_m':'Auditointirivin laskennallinen pituus metreinä, pyöristetty 0,001 metriin. Viivoja ei ole yhdistetty eikä yksinkertaistettu. Täsmälleen nollapituuteen romahtaneet geometriat, joiden pituus_m=0, ohitetaan ja niiden määrä kirjataan.',
            'lahtotasot':'osm_* -tasoilla ovat analyysin välimuistin väylät kuntarajan + 30 m puskurissa (20 m etäisyysrajalla). Muiden highway-luokkien ja tagisäännöillä ennen laskentaa hylättyjen väylien geometrioita ei ole mukana.',
            'mukaan_m':'OSM-lähtöväylän mukaan laskettu jalkakäytäväpituus kuntarajan sisällä. Ajoradalla voi olla kaksi puolta, joten luku voi ylittää viivapituuden.',
            'kadunvarsi_m':'OSM-lähtöväylän auditointiosuuksien summa, myös yhdistetyt ja tuntemattomat mukana. Nolla tarkoittaa, ettei välimuistin väylällä ole auditointiosumia.',
            'osm_lisenssi':'© OpenStreetMap contributors · ODbL · https://www.openstreetmap.org/copyright',
            'tarkistustila':'Pintatietoon ja geometriaan perustuva rajaus; käyttäjän ensimmäinen karttatarkistus huomioitu. Ei maastovarmennettu.',
            'hylkayssyy':'Lähtöväylän poissulun syy. Puuttuva footway=sidewalk tai pinta ei ole poissulkusyy.',
            'pinnan_tila':'osm_tieto = pinta tulee OSM:stä. oletus_asfaltti = pintatieto puuttuu ja laskennassa oletetaan asfaltti. Alkuperäisiä surface-tägejä ei muuteta.',
            'rinnakkaiset_vaylat':'Lähimmän saman kadunpuolen kulkukelpoisen jalankulkuväylän takaiset rinnakkaiset osuudet poistetaan. varjossa_m on suoraan poistetun geometrian pituus; lyhyet jäljelle jäävät footway-jaksot voivat poistua lisäksi 15 m säännöllä. estaja_osm ja viitekatu_osm kertovat OSM-tunnisteet.',
        }
        with closing(sqlite3.connect(partial)) as db:
            db.execute('CREATE TABLE laskentatiedot (fid INTEGER PRIMARY KEY, avain TEXT NOT NULL UNIQUE, arvo TEXT NOT NULL)')
            db.executemany('INSERT INTO laskentatiedot (avain,arvo) VALUES (?,?)',info.items())
            db.execute("INSERT INTO gpkg_contents (table_name,data_type,identifier,description,srs_id) VALUES ('laskentatiedot','attributes','laskentatiedot','Laskennan lähteet, parametrit ja tasojen tulkinta',NULL)")
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('GeoPackagen eheystarkistus epäonnistui.')
            for name,count in manifest.items():
                if db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] != count:
                    raise ValueError(f'Kohdemäärä ei täsmää: {name}')
            db.commit()
        partial.replace(target)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    print(f'Valmis: {target.resolve()}',flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code', default='564')
    parser.add_argument('--results', default='data/results')
    parser.add_argument('--cache', default='data/cache/finland.db')
    parser.add_argument('--output')
    args = parser.parse_args()
    code = args.code.zfill(3)
    output = args.output or f'data/exports/{"oulu" if code=="564" else code}_analyysi.gpkg'
    export_gpkg(Path(args.results)/f'{code}.json',Path(args.results)/f'{code}.segments.geojson',args.cache,output)


if __name__ == '__main__':
    main()
