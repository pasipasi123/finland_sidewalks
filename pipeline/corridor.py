"""Keep the innermost mapped walking route on each side of a street."""
import math
from shapely import union_all
from shapely.geometry import LineString, Polygon
from shapely.strtree import STRtree
from .rules import sidewalk_absent

def direction_runs(line,max_turn_degrees=45):
    """Split connected lines at sharp turns; connectivity alone is not continuity."""
    coords=list(line.coords)
    run=[coords[0]]
    previous=None
    threshold=math.cos(math.radians(max_turn_degrees))
    for a,b in zip(coords,coords[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        length=math.hypot(dx,dy)
        if length<=1e-8:
            continue
        direction=(dx/length,dy/length)
        if previous is not None and previous[0]*direction[0]+previous[1]*direction[1]<threshold:
            if len(run)>1:
                yield LineString(run)
            run=[a]
        run.append(b)
        previous=direction
    if len(run)>1:
        yield LineString(run)

def flat_lines(geom):
    if geom.is_empty:
        return
    if geom.geom_type=='LineString':
        if geom.length>1e-6:
            yield geom
    elif hasattr(geom,'geoms'):
        for member in geom.geoms:
            yield from flat_lines(member)

def filter_outer_paths(candidates,roads,distance,level,alignment,progress=None,only_ids=None,confirmed_ids=(),junction_connections=()):
    """Return kept pieces and exact shadow intersections, without extending end caps.

    roads includes living_street references solely to reject their adjacent paths.
    A shared/unknown cycleway can be a blocker even though it is not counted.
    """
    records=[(oid,tags,kind,line) for oid,tags,kind,geom in candidates for line in flat_lines(geom)]
    road_geoms=[r[2] for r in roads]
    road_tree=STRtree(road_geoms)
    path_tree=STRtree([r[3] for r in records])
    kept=[]
    removed=[]
    tolerance=.25  # metres: don't decide street-side order from coordinate noise.
    cos30=math.cos(math.radians(30))
    for number,(oid,tags,kind,part) in enumerate(records,1):
        if only_ids is not None and oid not in only_ids:continue
        if progress and number%20000==0:
            progress(f'Lähimmän kadunvarsiväylän vertailu {number:,}/{len(records):,}')
        if kind not in {'footway','segregated'}:
            kept.append((oid,tags,kind,part))
            continue
        nearby=road_tree.query(part.buffer(distance))
        mid=part.interpolate(.5,normalized=True)
        suitable=[int(i) for i in nearby if level(tags)==level(roads[int(i)][1]) and alignment(part,road_geoms[int(i)])>=cos30 and part.distance(road_geoms[int(i)])<=distance]
        if not suitable:
            kept.append((oid,tags,kind,part))
            continue
        ri=min(suitable,key=lambda i:(mid.distance(road_geoms[i]),roads[i][0],i))
        road_id,road_tags,road=roads[ri]
        if road_tags.get('highway')=='living_street':
            removed.append({'osm_id':oid,'category':kind,'reason':'pihakadun_varsi','road_id':road_id,'blockers':[],'geometry':part})
            continue
        x,y=road.coords[0]
        dx,dy=road.coords[-1][0]-x,road.coords[-1][1]-y
        norm=math.hypot(dx,dy)
        ux,uy=dx/norm,dy/norm
        signed=ux*(mid.y-y)-uy*(mid.x-x)
        side='left' if signed>0 else 'right'
        if kind=='footway' and oid not in confirmed_ids and abs(signed)>tolerance and sidewalk_absent(road_tags,side) and tags.get('footway')!='sidewalk' and tags.get('is_sidepath')!='yes':
            removed.append({'osm_id':oid,'category':kind,'reason':'ajoradan_puolella_ei_jalkakaytavaa','road_id':road_id,'blockers':[],'geometry':part})
            continue
        if abs(signed)<=tolerance:
            kept.append((oid,tags,kind,part))
            continue
        sign=1 if signed>0 else -1
        nx,ny=-uy*sign,ux*sign
        shadows=[]
        blockers=set()
        for index in path_tree.query(part.buffer(distance)):
            bid,btags,bkind,blocker=records[int(index)]
            if bid==oid or level(btags)!=level(tags) or alignment(part,blocker)<cos30:
                continue
            # A verified intersection link joins this sidewalk at a real OSM
            # node. Its curving approach is not a competing outer parallel way.
            if (oid,bid) in junction_connections:continue
            coords=list(blocker.coords)
            # Only same-side, genuinely closer route fragments can cast a shadow.
            lateral=[sign*(ux*(py-y)-uy*(px-x)) for px,py in (coords[0],coords[-1])]
            if min(lateral)<=tolerance or sum(lateral)/2>=abs(signed)-tolerance:
                continue
            a,b=coords[0],coords[-1]
            reach=distance*3
            shadow=Polygon([a,b,(b[0]+nx*reach,b[1]+ny*reach),(a[0]+nx*reach,a[1]+ny*reach)])
            if not shadow.is_valid or part.intersection(shadow).length<=1e-6:
                continue
            shadows.append(shadow)
            blockers.add(bid)
        if not shadows:
            kept.append((oid,tags,kind,part))
            continue
        shadow=union_all(shadows)
        hidden=part.intersection(shadow)
        for line in flat_lines(part.difference(shadow)):
            kept.append((oid,tags,kind,line))
        if hidden.length>1e-6:
            removed.append({'osm_id':oid,'category':kind,'reason':'lahempi_jalankulkuvayla','road_id':road_id,'blockers':sorted(blockers),'geometry':hidden})
    return kept,removed
