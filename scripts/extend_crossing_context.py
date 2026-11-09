"""Add walking crossings as context without a country-sized node index."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

import osmium
from shapely.geometry import LineString
from pipeline.cli import TO_METRES,transform
from pipeline.rules import candidate_category


def extend(pbf='data/raw/finland.osm.pbf',cache='data/cache/finland.db'):
    with sqlite3.connect(cache) as db:
        meta=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
        if meta.get('cache_selection_version',1)<3:
            raise ValueError('Extend reference roads and walking candidates first')
        if meta.get('cache_selection_version',1)>=4:
            print('Ylityskonteksti on jo välimuistissa',flush=True)
            return 0
        with Path(pbf).open('rb') as source:
            if hashlib.file_digest(source,'sha256').hexdigest()!=meta['sha256']:
                raise ValueError('Source PBF mismatch')
        ways=[]
        needed=set()
        selected=osmium.filter.TagFilter(('footway','crossing'),('cycleway','crossing'))
        for way in osmium.FileProcessor(pbf,entities=osmium.osm.WAY).with_filter(selected):
            tags=dict(way.tags)
            if candidate_category(tags)!='crossing_context':continue
            refs=[node.ref for node in way.nodes]
            ways.append((way.id,tags,refs));needed.update(refs)
        print(f'{len(ways):,} jalankulun ylitysviivaa; {len(needed):,} tarvittavaa solmua',flush=True)
        points={}
        for node in osmium.FileProcessor(pbf,entities=osmium.osm.NODE).with_filter(osmium.filter.IdFilter(needed)):
            points[node.id]=(node.location.lon,node.location.lat)
        missing=needed-points.keys()
        if missing:raise ValueError(f'{len(missing)} missing crossing nodes')
        added=0
        for oid,tags,refs in ways:
            if len(refs)<2 or db.execute('SELECT 1 FROM ways WHERE id=?',(oid,)).fetchone():continue
            geom=transform(TO_METRES,LineString([points[ref] for ref in refs]))
            if not geom.length:continue
            x1,y1,x2,y2=geom.bounds
            db.execute('INSERT INTO ways VALUES (?,?,?)',(oid,json.dumps(tags),geom.wkb))
            db.execute('INSERT INTO bounds VALUES (?,?,?,?,?)',(oid,x1,x2,y1,y2));added+=1
        meta.update(cache_selection_version=4,crossing_selection_version='1.6.1',added_crossing_ways=added)
        db.execute('UPDATE metadata SET value=?',(json.dumps(meta),))
        db.commit()
        print(f'Valmis: {added:,} ylitysviivaa lisätty kontekstiksi',flush=True)
        return added


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pbf',default='data/raw/finland.osm.pbf')
    parser.add_argument('--cache',default='data/cache/finland.db')
    args=parser.parse_args()
    extend(args.pbf,args.cache)
