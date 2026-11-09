"""Short links need sidewalk support plus another sidewalk or a crossing."""
from shapely.geometry import Point
from shapely.strtree import STRtree
from shapely.ops import substring
from .rules import category
from .network import NETWORK_POLICY

CORNER_POLICY={'max_link_m':40,'extra_distance_m':10,'max_distance_m':30,'endpoint_tolerance_m':0.002,'sample_m':5,
               'max_extension_m':30,'min_included_fraction':0.7,'crossing_can_anchor_link':True}

def sidewalk_end_extensions(ways,supports,network,distance):
    by_id={}
    for oid,_,part in supports:by_id.setdefault(oid,[]).append(part)
    extensions=[]
    for oid,tags,geom in ways:
        parts=by_id.get(oid)
        if not parts or category(tags)!='footway' or (tags.get('footway')!='sidewalk' and tags.get('is_sidepath')!='yes'):continue
        if sum(p.length for p in parts)<CORNER_POLICY['min_included_fraction']*geom.length:continue
        positions=[geom.project(Point(p)) for part in parts for p in part.coords]
        for start,end,coord in [(0,min(positions),geom.coords[0]),(max(positions),geom.length,geom.coords[-1])]:
            if not 0.01<end-start<=CORNER_POLICY['max_extension_m']:continue
            lev=network.level(tags)
            if network.distance(network.intersections,network.key(lev,coord))>NETWORK_POLICY['junction_tolerance_m']:continue
            line=substring(geom,start,end)
            keys=[network.key(lev,p) for p in line.segmentize(CORNER_POLICY['sample_m']).coords]
            limit=min(distance+CORNER_POLICY['extra_distance_m'],CORNER_POLICY['max_distance_m'])
            if max(network.distance(network.streets,key) for key in keys)>limit:continue
            if max(network.distance(network.intersections,key) for key in keys)>NETWORK_POLICY['junction_tolerance_m']:continue
            extensions.append((oid,tags,line))
    return extensions

def supported_corner_links(ways,supports,network,distance):
    if not supports:return []
    tree=STRtree([row[2] for row in supports])
    included={row[0] for row in supports}
    links=[]
    for oid,tags,geom in ways:
        if oid in included or category(tags)!='footway' or not 0<geom.length<=CORNER_POLICY['max_link_m']:continue
        if network.rejection(tags,geom):continue
        lev=network.level(tags)
        ends=[]
        crossings=[]
        for coord in [geom.coords[0],geom.coords[-1]]:
            p=Point(coord)
            connected=network.walking_ids.get(network.key(lev,coord),set())
            crossings.append(bool(network.crossing_nodes.get(network.key(lev,coord))))
            matches=tree.query(p.buffer(CORNER_POLICY['endpoint_tolerance_m']))
            ends.append({supports[int(i)][0] for i in matches if supports[int(i)][0] in connected and network.level(supports[int(i)][1])==lev and p.distance(supports[int(i)][2])<=CORNER_POLICY['endpoint_tolerance_m']})
        keys=[network.key(lev,p) for p in geom.segmentize(CORNER_POLICY['sample_m']).coords]
        between_sidewalks=bool(ends[0] and ends[1] and any(a!=b for a in ends[0] for b in ends[1]))
        crossing_link=bool((ends[0] and crossings[1]) or (ends[1] and crossings[0]))
        if not between_sidewalks and not crossing_link:continue
        if not crossing_link and min(network.distance(network.junctions,key) for key in keys)>NETWORK_POLICY['junction_tolerance_m']:continue
        limit=min(distance+CORNER_POLICY['extra_distance_m'],CORNER_POLICY['max_distance_m'])
        if max(network.distance(network.streets,key) for key in keys)>limit:continue
        links.append((oid,tags,geom))
    return links
