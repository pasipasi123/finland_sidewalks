"""Short links need sidewalk support plus another sidewalk or a crossing."""
from shapely.geometry import Point
from shapely.geometry import LineString
from collections import defaultdict
from shapely.strtree import STRtree
from shapely.ops import substring
from .rules import category
from .network import NETWORK_POLICY

CORNER_POLICY={'max_link_m':40,'extra_distance_m':10,'max_distance_m':30,'endpoint_tolerance_m':0.002,'sample_m':5,
               'max_extension_m':30,'min_included_fraction':0.7,'crossing_can_anchor_link':True,
               'repair_internal_gaps':True,'repair_way_chains':True,'two_anchor_midblock_distance_m':20}

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

def merge_link_intervals(ways,links):
    """Avoid counting overlapping repairs of the same original way twice."""
    sources={oid:(tags,geom) for oid,tags,geom in ways}
    intervals=defaultdict(list)
    for oid,_,line in links:
        geom=sources[oid][1]
        positions=[geom.project(Point(p)) for p in line.coords]
        intervals[oid].append((min(positions),max(positions)))
    result=[]
    for oid,spans in intervals.items():
        tags,geom=sources[oid];merged=[]
        for start,end in sorted(spans):
            if merged and start<=merged[-1][1]+0.001:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
            else:merged.append((start,end))
        result.extend((oid,tags,substring(geom,start,end)) for start,end in merged if end-start>0.001)
    return result

def supported_missing_chains(ways,supports,network,distance):
    """Connect accepted portions through short missing bends across way IDs.

    Accepted pieces split the graph, including within an individual OSM way.
    Unanchored leaves are pruned, so an estate spur cannot justify itself.
    """
    if not supports:return []
    by_id=defaultdict(list)
    for oid,_,part in supports:by_id[oid].append(part)
    graph=defaultdict(set);edge_rows=defaultdict(list);owners=defaultdict(set);locations={}
    for oid,tags,geom in ways:
        if category(tags)!='footway':continue
        parts=by_id.get(oid,[])
        if not parts and geom.length>CORNER_POLICY['max_link_m']:continue
        if network.rejection(tags,geom):continue
        spans=[]
        for part in parts:
            p=[geom.project(Point(coord)) for coord in part.coords];spans.append((min(p),max(p)))
        merged=[]
        for start,end in sorted(spans):
            if merged and start<=merged[-1][1]+0.01:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
            else:merged.append((start,end))
        gaps=[];cursor=0
        for start,end in merged:
            if start-cursor>0.01:gaps.append((cursor,start))
            cursor=max(cursor,end)
        if geom.length-cursor>0.01:gaps.append((cursor,geom.length))
        for start,end in gaps:
            if end-start>CORNER_POLICY['max_link_m']:continue
            line=substring(geom,start,end);coords=list(line.coords);lev=network.level(tags)
            for p,q in zip(coords,coords[1:]):
                a,b=network.key(lev,p),network.key(lev,q)
                if a==b:continue
                edge=tuple(sorted((a,b)));graph[a].add(b);graph[b].add(a)
                edge_rows[edge].append((oid,tags,LineString([p,q])))
                for key,coord in [(a,p),(b,q)]:owners[key].add(oid);locations[key]=coord
    tree=STRtree([row[2] for row in supports]);anchors=set();crossings=set()
    for key,coord in locations.items():
        point=Point(coord);connected=owners[key] | network.walking_ids.get(key,set())
        for index in tree.query(point.buffer(CORNER_POLICY['endpoint_tolerance_m'])):
            oid,tags,line=supports[int(index)]
            if oid in connected and network.level(tags)==key[0] and point.distance(line)<=CORNER_POLICY['endpoint_tolerance_m']:
                anchors.add(key);break
        if network.crossing_nodes.get(key):crossings.add(key)
    unseen=set(graph);links=[]
    while unseen:
        seed=unseen.pop();component={seed};stack=[seed]
        while stack:
            for neighbor in graph[stack.pop()]:
                if neighbor in unseen:unseen.remove(neighbor);component.add(neighbor);stack.append(neighbor)
        remaining=set(component);protected=anchors | crossings
        leaves=[key for key in remaining if len(graph[key])==1 and key not in protected]
        while leaves:
            key=leaves.pop()
            if key not in remaining:continue
            remaining.remove(key)
            leaves.extend(neighbor for neighbor in graph[key] if neighbor in remaining and neighbor not in protected and len(graph[neighbor] & remaining)<=1)
        core=anchors & remaining;cross=crossings & remaining
        if len(core)<2 and not any(a!=b for a in core for b in cross):continue
        edges={tuple(sorted((a,b))) for a in remaining for b in graph[a] if b in remaining}
        if not edges or len(edges)>=len(remaining):continue
        rows=[row for edge in edges for row in edge_rows[edge]]
        if sum(line.length for _,_,line in rows)>CORNER_POLICY['max_link_m']:continue
        near_junction=any(network.distance(network.intersections,key)<=NETWORK_POLICY['junction_tolerance_m'] for key in remaining)
        sampled=[network.distance(network.streets,network.key(network.level(tags),p)) for _,tags,line in rows for p in line.segmentize(CORNER_POLICY['sample_m']).coords]
        midblock=(len(core)>=2 and max(sampled)<=min(distance,CORNER_POLICY['two_anchor_midblock_distance_m']))
        if not cross and not near_junction and not midblock and not any(key in network.street_graph for key in remaining):continue
        limit=min(distance+CORNER_POLICY['extra_distance_m'],CORNER_POLICY['max_distance_m'])
        if max(sampled)>limit:continue
        links.extend(rows)
    return merge_link_intervals(ways,links)
