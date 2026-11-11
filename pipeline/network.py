"""Conservative graph context for incidental street matches of interior paths."""
import math
from collections import defaultdict
from shapely.geometry import Point
from shapely.strtree import STRtree
from .rules import candidate_category,reference_road

NETWORK_POLICY={'junction_tolerance_m':25,'max_chain_trace_m':250,'interior_margin_m':5,'node_round_m':0.001,
                'street_return_min_offset_m':6,'street_return_min_angle_degrees':55,'excursion_sample_m':10}

class WalkingNetwork:
    def __init__(self,ways,level,street_distance=20):
        self.level=level
        self.limit=street_distance
        self.walk=defaultdict(set)
        self.walking_ids=defaultdict(set)
        self.crossing_nodes=defaultdict(set)
        street_graph=defaultdict(set)
        streets=defaultdict(list)
        for oid,tags,geom in ways:
            lev=level(tags)
            kind=candidate_category(tags)
            if kind=='crossing_context' and tags.get('foot',tags.get('access'))!='destination':
                for point in geom.coords:self.crossing_nodes[self.key(lev,point)].add(oid)
            graph=self.walk if kind in {'footway','segregated','shared','unknown'} else street_graph if kind in {'road','road_context'} else None
            if graph is not None:
                coords=[self.key(lev,p) for p in geom.coords]
                if graph is self.walk:
                    for key in coords:self.walking_ids[key].add(oid)
                for a,b in zip(coords,coords[1:]):
                    if a!=b:graph[a].add(b);graph[b].add(a)
            if reference_road(tags):streets[lev].append(geom)
        junctions=defaultdict(list)
        intersections=defaultdict(list)
        for key,neighbors in street_graph.items():
            if len(neighbors)!=2:junctions[key[0]].append(Point(key[1],key[2]))
            if len(neighbors)>=3:intersections[key[0]].append(Point(key[1],key[2]))
        self.streets={lev:STRtree(gs) for lev,gs in streets.items()}
        self.junctions={lev:STRtree(gs) for lev,gs in junctions.items()}
        self.intersections={lev:STRtree(gs) for lev,gs in intersections.items()}
        self.street_graph=street_graph
        self.cache={}

    def isolated_rejections(self,ways,kept,ignored_continuations=()):
        """Reject a dangling candidate whose only continuation was rejected.

        Join active ways through degree-two nodes first, so OSM way splitting
        cannot let mutually supporting fragments survive. An internal estate
        branch on a continuous street spine does not meet this endpoint test.
        """
        active={oid for oid,_,kind,_ in kept if not kind.startswith('blocker_only')}
        parents={oid:oid for oid in active}
        def root(oid):
            while parents[oid]!=oid:
                parents[oid]=parents[parents[oid]];oid=parents[oid]
            return oid
        for key,ids in self.walking_ids.items():
            members=ids & active
            if len(self.walk[key])==2 and len(members)>1:
                first=next(iter(members))
                for oid in members:parents[root(oid)]=root(first)
        groups=defaultdict(list)
        for oid,tags,geom in ways:
            if oid in active:groups[root(oid)].append((oid,tags,geom))
        rejected={}
        for records in groups.values():
            if any(candidate_category(tags)!='footway' or tags.get('footway')=='sidewalk' or tags.get('is_sidepath')=='yes' for _,tags,_ in records):continue
            ids={oid for oid,_,_ in records}
            graph=defaultdict(set)
            for _,tags,geom in records:
                keys=[self.key(self.level(tags),p) for p in geom.coords]
                for a,b in zip(keys,keys[1:]):
                    if a!=b:graph[a].add(b);graph[b].add(a)
            ends=[key for key,neighbors in graph.items() if len(neighbors)==1]
            if len(ends)!=2 or any(len(neighbors)>2 for neighbors in graph.values()):continue
            if not any(len(self.walk[key])==1 for key in ends):continue
            if any(self.distance(self.junctions,key)<=NETWORK_POLICY['junction_tolerance_m'] for key in graph):continue
            for key in ends:
                others=self.walking_ids[key]-ids-set(ignored_continuations)
                if others and not (others & active):
                    rejected.update({oid:'irrallinen_haara_hylatysta_reitista' for oid in ids})
                    break
        return rejected

    @staticmethod
    def key(level,point):
        return (level,round(point[0],3),round(point[1],3))

    def distance(self,trees,key):
        tree=trees.get(key[0])
        if tree is None or len(tree.geometries)==0:return float('inf')
        point=Point(key[1],key[2])
        return point.distance(tree.geometries[int(tree.nearest(point))])

    def endpoint(self,start,previous,protect_junctions=True):
        state=(start,previous,protect_junctions)
        if state in self.cache:return self.cache[state]
        current=start;seen=set();length=0
        while True:
            if protect_junctions and self.distance(self.junctions,current)<=NETWORK_POLICY['junction_tolerance_m']:
                result=(current,True);break
            neighbors=self.walk.get(current,set())
            if len(neighbors)!=2:
                result=(current,False);break
            if current in seen or length>NETWORK_POLICY['max_chain_trace_m']:
                result=(current,True);break
            seen.add(current)
            next_nodes=neighbors-{previous}
            if len(next_nodes)!=1:
                result=(current,False);break
            following=next(iter(next_nodes))
            length+=math.hypot(following[1]-current[1],following[2]-current[2])
            previous,current=current,following
        self.cache[state]=result
        return result

    def street_return(self,keys):
        """An unbranched estate detour attached perpendicularly to carriageways.

        Both real graph ends must touch road nodes; merely being near a road
        is insufficient. Protect a normal connection between two junctions.
        """
        if any(len(self.walk[key])!=2 for key in keys[1:-1]):return False
        ends=[self.endpoint(keys[0],keys[1],False),self.endpoint(keys[-1],keys[-2],False)]
        if any(protected or len(self.walk[key])!=1 or key not in self.street_graph for key,protected in ends):return False
        if all(self.distance(self.junctions,key)<=NETWORK_POLICY['junction_tolerance_m'] for key,_ in ends):return False
        if max(self.distance(self.streets,key) for key in keys)<NETWORK_POLICY['street_return_min_offset_m']:return False
        threshold=math.cos(math.radians(NETWORK_POLICY['street_return_min_angle_degrees']))
        for key,_ in ends:
            neighbor=next(iter(self.walk[key]))
            dx,dy=neighbor[1]-key[1],neighbor[2]-key[2]
            norm=math.hypot(dx,dy)
            for road_node in self.street_graph[key]:
                rx,ry=road_node[1]-key[1],road_node[2]-key[2]
                if abs(dx*rx+dy*ry)>threshold*norm*math.hypot(rx,ry):return False
        return True

    def excursion_rejection(self,tags,geom):
        """Judge an entire unbranched route, not its incidentally parallel piece.

        Follow way boundaries to genuine walking branches. A near-street
        walking branch provides a meaningful split between spine and access.
        Carriageway junction proximity alone does not establish that split.
        """
        coords=list(geom.coords)
        if len(coords)<2 or coords[0]==coords[-1]:return None
        lev=self.level(tags)
        keys=[self.key(lev,p) for p in coords]
        context=set(keys)
        edges=list(zip(keys,keys[1:]))
        for start,previous in [(keys[0],keys[1]),(keys[-1],keys[-2])]:
            current=start;seen={previous};length=0
            while len(self.walk.get(current,set()))==2:
                following=self.walk[current]-{previous}
                if len(following)!=1:return None
                following=next(iter(following))
                if following in seen:return None
                length+=math.hypot(following[1]-current[1],following[2]-current[2])
                if length>NETWORK_POLICY['max_chain_trace_m']:return None
                seen.add(current);context.add(following)
                edges.append((current,following))
                previous,current=current,following
        # Long straight edges may cut away from a curving street even when
        # their mapped endpoints are near it. Sample the complete chain too.
        for a,b in edges:
            count=math.ceil(math.hypot(b[1]-a[1],b[2]-a[2])/NETWORK_POLICY['excursion_sample_m'])
            for step in range(1,count):
                context.add(self.key(lev,(a[1]+(b[1]-a[1])*step/count,a[2]+(b[2]-a[2])*step/count)))
        distances={key:self.distance(self.streets,key) for key in context}
        if any(len(self.walk.get(key,set()))>=3 and distance<=self.limit for key,distance in distances.items()):return None
        if min(distances.values())<=self.limit and max(distances.values())>self.limit+NETWORK_POLICY['interior_margin_m']:
            return 'ajoradasta_poikkeava_kokonaisreitti'
        return None

    def rejection(self,tags,geom):
        return self.endpoint_rejection(tags,geom) or self.excursion_rejection(tags,geom)

    def endpoint_rejection(self,tags,geom):
        coords=list(geom.coords)
        if len(coords)<2 or coords[0]==coords[-1]:return None
        lev=self.level(tags)
        keys=[self.key(lev,p) for p in coords]
        if self.street_return(keys):return 'ajoradalta_sivuun_ja_takaisin'
        ends=[self.endpoint(self.key(lev,coords[0]),self.key(lev,coords[1])),
              self.endpoint(self.key(lev,coords[-1]),self.key(lev,coords[-2]))]
        if any(protected for _,protected in ends):return None
        degrees=[len(self.walk.get(key,set())) for key,_ in ends]
        distances=[self.distance(self.streets,key) for key,_ in ends]
        # An unmapped entrance / dead end deep in an estate is also interior
        # context; it need not be a branching network node.
        interior=[(degrees[i]==1 or degrees[i]>=3) and distances[i]>self.limit+NETWORK_POLICY['interior_margin_m'] for i in range(2)]
        terminal=[degrees[i]==1 and distances[i]<=self.limit for i in range(2)]
        if (interior[0] and terminal[1]) or (interior[1] and terminal[0]):
            return 'sisaverkon_paattyva_katuosuma'
        if all(interior):return 'sisaverkon_lapi_kulkeva_katuosuma'
        return None
