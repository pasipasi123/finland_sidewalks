"""Add street references excluded by the v1 carriageway foot/access interpretation."""
import json
import hashlib
import sqlite3
from pathlib import Path
import osmium
from shapely import from_wkt
from pipeline.cli import TO_METRES,transform
from pipeline.rules import ROADS,reference_road

db=sqlite3.connect('data/cache/finland.db')
metadata=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
with Path('data/raw/finland.osm.pbf').open('rb') as source:
    if hashlib.file_digest(source,'sha256').hexdigest()!=metadata['sha256']:
        raise ValueError('PBF does not match cached source snapshot')
factory=osmium.geom.WKTFactory()
class Extend(osmium.SimpleHandler):
    count=0
    def way(self,way):
        if way.tags.get('highway') not in ROADS:
            return
        if way.tags.get('foot') not in {'no','private'} and way.tags.get('access')!='no':
            return
        tags=dict(way.tags)
        if not reference_road(tags) or db.execute('SELECT 1 FROM ways WHERE id=?',(way.id,)).fetchone():
            return
        geom=transform(TO_METRES,from_wkt(factory.create_linestring(way)))
        if not geom.length:
            return
        x1,y1,x2,y2=geom.bounds
        db.execute('INSERT INTO ways VALUES (?,?,?)',(way.id,json.dumps(tags),geom.wkb))
        db.execute('INSERT INTO bounds VALUES (?,?,?,?,?)',(way.id,x1,x2,y1,y2))
        self.count+=1
        if self.count%1000==0:
            print(f'{self.count:,} puuttunutta ajorataviitettä lisätty',flush=True)

handler=Extend()
try:
    handler.apply_file('data/raw/finland.osm.pbf',locations=True,idx='sparse_file_array,data/cache/extend.nodes')
    metadata['cache_selection_version']=max(metadata.get('cache_selection_version',1),2)
    metadata['reference_selection_version']='1.1.0'
    metadata['added_reference_ways']=metadata.get('added_reference_ways',0)+handler.count
    db.execute('UPDATE metadata SET value=?',(json.dumps(metadata),))
    db.commit()
    print(f'Valmis: {handler.count} puuttunutta ajorataa lisätty.',flush=True)
except Exception:
    db.rollback()
    raise
finally:
    db.close()
