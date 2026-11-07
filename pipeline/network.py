"""Conservative graph context for incidental street matches of interior paths."""
import math
from collections import defaultdict
from shapely.geometry import Point
from shapely.strtree import STRtree
from .rules import candidate_category,reference_road

NETWORK_POLICY={'junction_tolerance_m':25,'max_chain_trace_m':250,'interior_margin_m':5,'node_round_m':0.001}

class WalkingNetwork:
    def __init__(self,ways,level,street_distance=20):
        self.level=level
        self.limit=street_distance
        self.walk=defaultdict(set)
        street_graph=defaultdict(set)
        streets=defaultdict(list)
        for _,tags,geom in ways:
            lev=level(tags)
            kind=candidate_category(tags)
            graph=self.walk if kind in {'footway','segregated','shared','unknown'} else street_graph if kind in {'road','road_context'} else None
            if graph is not None:
                coords=[self.key(lev,p) for p in geom.coords]
                for a,b in zip(coords,coords[1:]):
                    if a!=b:graph[a].add(b);graph[b].add(a)
            if reference_road(tags):streets[lev].append(geom)
        junctions=defaultdict(list)
        for key,neighbors in street_graph.items():
            if len(neighbors)!=2:junctions[key[0]].append(Point(key[1],key[2]))
        self.streets={lev:STRtree(gs) for lev,gs in streets.items()}
        self.junctions={lev:STRtree(gs) for lev,gs in junctions.items()}
        self.cache={}

    @staticmethod
    def key(level,point):
        return (level,round(point[0],3),round(point[1],3))

    def distance(self,trees,key):
        tree=trees.get(key[0])
        if tree is None or len(tree.geometries)==0:return float('inf')
        point=Point(key[1],key[2])
        return point.distance(tree.geometries[int(tree.nearest(point))])

    def endpoint(self,start,previous):
        state=(start,previous)
        if state in self.cache:return self.cache[state]
        current=start;seen=set();length=0
        while True:
            if self.distance(self.junctions,current)<=NETWORK_POLICY['junction_tolerance_m']:
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

    def rejection(self,tags,geom):
        coords=list(geom.coords)
        if len(coords)<2 or coords[0]==coords[-1]:return None
        lev=self.level(tags)
        ends=[self.endpoint(self.key(lev,coords[0]),self.key(lev,coords[1])),
              self.endpoint(self.key(lev,coords[-1]),self.key(lev,coords[-2]))]
        if any(protected for _,protected in ends):return None
        degrees=[len(self.walk.get(key,set())) for key,_ in ends]
        distances=[self.distance(self.streets,key) for key,_ in ends]
        interior=[degrees[i]>=3 and distances[i]>self.limit+NETWORK_POLICY['interior_margin_m'] for i in range(2)]
        terminal=[degrees[i]==1 and distances[i]<=self.limit for i in range(2)]
        if (interior[0] and terminal[1]) or (interior[1] and terminal[0]):
            return 'sisaverkon_paattyva_katuosuma'
        if all(interior):return 'sisaverkon_lapi_kulkeva_katuosuma'
        return None
