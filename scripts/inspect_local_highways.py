"""Read unfiltered highway/parking tags from the pinned PBF in a small WGS84 box."""
import argparse
import json
from pathlib import Path
import osmium

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bbox',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
x1,y1,x2,y2=map(float,args.bbox.split(','))
records=[]
class Inspect(osmium.SimpleHandler):
    def way(self,way):
        if not way.tags.get('highway') and way.tags.get('amenity')!='parking':
            return
        if not any(x1<n.lon<x2 and y1<n.lat<y2 for n in way.nodes):
            return
        records.append({'id':way.id,'tags':dict(way.tags),'coordinates':[(n.lon,n.lat) for n in way.nodes]})
index=Path('data/cache')/(Path(args.output).stem+'.nodes')
Inspect().apply_file('data/raw/finland.osm.pbf',locations=True,idx='sparse_file_array,'+str(index))
Path(args.output).write_text(json.dumps(records,ensure_ascii=False),encoding='utf-8')
print(f'{len(records)} paikallista highway/parking-kohdetta luettu.',flush=True)
