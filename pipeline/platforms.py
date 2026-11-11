"""Mapped platform areas identify short terminal boarding-access footways."""
from shapely.geometry import Point,Polygon
from shapely.strtree import STRtree
from .rules import category

PLATFORM_POLICY={'max_access_way_m':100,'endpoint_tolerance_m':0.25,
                 'other_endpoint_outside_m':3,'inside_fraction':0.8,
                 'explicit_sidewalk_protected':True}
PLATFORM_SCHEMA='CREATE TABLE IF NOT EXISTS platforms(id INTEGER PRIMARY KEY,tags TEXT,geom BLOB); CREATE VIRTUAL TABLE IF NOT EXISTS platform_bounds USING rtree(id,minx,maxx,miny,maxy);'

def platform_polygon(tags,line):
    if tags.get('public_transport')!='platform' and tags.get('highway')!='platform':return None
    if tags.get('area')=='no' or not line.is_ring or len(line.coords)<4:return None
    polygon=Polygon(line.coords)
    return polygon if polygon.is_valid and polygon.area>0 else None

def platform_access_ways(ways,platforms,network):
    if not platforms:return {}
    tree=STRtree([area for _,_,area in platforms]);found={}
    for oid,tags,line in ways:
        if category(tags)!='footway' or tags.get('footway')=='sidewalk' or tags.get('is_sidepath')=='yes':continue
        if not 0<line.length<=PLATFORM_POLICY['max_access_way_m']:continue
        lev=network.level(tags)
        for endpoint,other in [(line.coords[0],line.coords[-1]),(line.coords[-1],line.coords[0])]:
            if len(network.walk.get(network.key(lev,endpoint),set()))!=1:continue
            point=Point(endpoint);opposite=Point(other)
            for index in tree.query(point.buffer(PLATFORM_POLICY['endpoint_tolerance_m'])):
                pid,ptags,area=platforms[int(index)]
                if network.level(ptags)!=lev or point.distance(area)>PLATFORM_POLICY['endpoint_tolerance_m']:continue
                if tags.get('level','0')!=ptags.get('level','0'):continue
                inside=line.intersection(area.buffer(PLATFORM_POLICY['endpoint_tolerance_m'])).length/line.length
                if opposite.distance(area)<PLATFORM_POLICY['other_endpoint_outside_m'] and inside<PLATFORM_POLICY['inside_fraction']:continue
                found.setdefault(oid,set()).add(pid)
    return {oid:sorted(ids) for oid,ids in found.items()}
