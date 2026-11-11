"""Cache closed OSM platform polygons as separate spatial context."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
import osmium
from shapely.geometry import LineString
from pipeline.cli import TO_METRES,transform
from pipeline.platforms import PLATFORM_SCHEMA,platform_polygon

def extend(pbf='data/raw/finland.osm.pbf',cache='data/cache/finland.db'):
    with sqlite3.connect(cache) as db:
        meta=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
        if meta.get('cache_selection_version',1)<5:raise ValueError('Extend earlier cache selections first')
        if meta.get('cache_selection_version',1)>=6:
            print('Laiturialueet ovat jo välimuistissa',flush=True);return 0
        with Path(pbf).open('rb') as source:
            if hashlib.file_digest(source,'sha256').hexdigest()!=meta['sha256']:raise ValueError('Source PBF mismatch')
        ways=[];needed=set()
        selected=osmium.filter.TagFilter(('public_transport','platform'),('highway','platform'))
        for way in osmium.FileProcessor(pbf,entities=osmium.osm.WAY).with_filter(selected):
            tags=dict(way.tags);refs=[n.ref for n in way.nodes]
            if tags.get('area')=='no' or len(refs)<4 or refs[0]!=refs[-1]:continue
            ways.append((way.id,tags,refs));needed.update(refs)
        print(f'{len(ways):,} suljettua laituriviivaa; {len(needed):,} tarvittavaa solmua',flush=True)
        points={n.id:(n.location.lon,n.location.lat) for n in osmium.FileProcessor(pbf,entities=osmium.osm.NODE).with_filter(osmium.filter.IdFilter(needed))} if needed else {}
        if needed-points.keys():raise ValueError('Missing platform nodes')
        db.executescript(PLATFORM_SCHEMA)
        count=0
        for oid,tags,refs in ways:
            line=transform(TO_METRES,LineString([points[ref] for ref in refs]));area=platform_polygon(tags,line)
            if area is None:continue
            x1,y1,x2,y2=area.bounds
            db.execute('INSERT INTO platforms VALUES (?,?,?)',(oid,json.dumps(tags),area.wkb))
            db.execute('INSERT INTO platform_bounds VALUES (?,?,?,?,?)',(oid,x1,x2,y1,y2));count+=1
        meta.update(cache_selection_version=6,platform_selection_version='1.6.3',platform_area_count=count)
        db.execute('UPDATE metadata SET value=?',(json.dumps(meta),));db.commit()
        print(f'Valmis: {count:,} laiturialuetta lisätty',flush=True)
        return count

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pbf',default='data/raw/finland.osm.pbf');parser.add_argument('--cache',default='data/cache/finland.db')
    args=parser.parse_args();extend(args.pbf,args.cache)
