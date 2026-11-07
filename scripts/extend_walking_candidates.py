"""Add footway+bicycle=designated ways whose implicit foot designation v1 missed."""
import hashlib
import json
import sqlite3
from pathlib import Path
import osmium
from shapely import from_wkt
from pipeline.cli import TO_METRES,transform
from pipeline.rules import candidate_category

db=sqlite3.connect('data/cache/finland.db')
meta=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
if meta.get('cache_selection_version',1)<2:
    raise ValueError('Extend reference roads first')
with Path('data/raw/finland.osm.pbf').open('rb') as source:
    if hashlib.file_digest(source,'sha256').hexdigest()!=meta['sha256']:
        raise ValueError('Source PBF mismatch')
factory=osmium.geom.WKTFactory()
class Extend(osmium.SimpleHandler):
    count=0
    def way(self,way):
        if way.tags.get('highway')!='footway' or way.tags.get('bicycle')!='designated' or way.tags.get('foot')=='designated':
            return
        tags=dict(way.tags)
        if not candidate_category(tags) or db.execute('SELECT 1 FROM ways WHERE id=?',(way.id,)).fetchone():
            return
        geom=transform(TO_METRES,from_wkt(factory.create_linestring(way)))
        if not geom.length:return
        x1,y1,x2,y2=geom.bounds
        db.execute('INSERT INTO ways VALUES (?,?,?)',(way.id,json.dumps(tags),geom.wkb))
        db.execute('INSERT INTO bounds VALUES (?,?,?,?,?)',(way.id,x1,x2,y1,y2))
        self.count+=1
        if self.count%1000==0:print(f'{self.count:,} puuttunutta footwayta lisätty',flush=True)
handler=Extend()
try:
    handler.apply_file('data/raw/finland.osm.pbf',locations=True,idx='sparse_file_array,data/cache/extend-walking.nodes')
    meta['cache_selection_version']=3
    meta['walking_selection_version']='1.3.0'
    meta['added_walking_ways']=meta.get('added_walking_ways',0)+handler.count
    db.execute('UPDATE metadata SET value=?',(json.dumps(meta),))
    db.commit()
    print(f'Valmis: {handler.count} puuttunutta footwayta lisätty',flush=True)
except Exception:
    db.rollback()
    raise
finally:
    db.close()
