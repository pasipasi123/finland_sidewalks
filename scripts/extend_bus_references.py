"""Add missing access=no streets with modal exceptions, including bus=yes."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

import osmium
from shapely.geometry import LineString
from pipeline.cli import TO_METRES,transform
from pipeline.rules import reference_road


def extend(pbf='data/raw/finland.osm.pbf',cache='data/cache/finland.db'):
    with sqlite3.connect(cache) as db:
        meta=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
        if meta.get('cache_selection_version',1)<4:
            raise ValueError('Extend the earlier reference, walking and crossing selections first')
        if meta.get('cache_selection_version',1)>=5:
            print('Bussikatujen ajorataviitteet ovat jo välimuistissa',flush=True)
            return 0
        with Path(pbf).open('rb') as source:
            if hashlib.file_digest(source,'sha256').hexdigest()!=meta['sha256']:
                raise ValueError('Source PBF mismatch')
        ways=[];needed=set()
        selected=osmium.filter.TagFilter(('access','no'))
        for way in osmium.FileProcessor(pbf,entities=osmium.osm.WAY).with_filter(selected):
            tags=dict(way.tags)
            if not reference_road(tags) or db.execute('SELECT 1 FROM ways WHERE id=?',(way.id,)).fetchone():continue
            refs=[node.ref for node in way.nodes]
            if len(refs)<2:continue
            ways.append((way.id,tags,refs));needed.update(refs)
        print(f'{len(ways):,} puuttuvaa ajorataviitettä; {len(needed):,} tarvittavaa solmua',flush=True)
        points={node.id:(node.location.lon,node.location.lat) for node in
                osmium.FileProcessor(pbf,entities=osmium.osm.NODE).with_filter(osmium.filter.IdFilter(needed))} if needed else {}
        if needed-points.keys():raise ValueError('Missing reference road nodes')
        added=0
        for oid,tags,refs in ways:
            geom=transform(TO_METRES,LineString([points[ref] for ref in refs]))
            if not geom.length:continue
            x1,y1,x2,y2=geom.bounds
            db.execute('INSERT INTO ways VALUES (?,?,?)',(oid,json.dumps(tags),geom.wkb))
            db.execute('INSERT INTO bounds VALUES (?,?,?,?,?)',(oid,x1,x2,y1,y2));added+=1
        meta.update(cache_selection_version=5,reference_selection_version='1.6.2',added_bus_reference_ways=added)
        meta['added_reference_ways']=meta.get('added_reference_ways',0)+added
        db.execute('UPDATE metadata SET value=?',(json.dumps(meta),));db.commit()
        print(f'Valmis: {added:,} ajorataviitettä lisätty',flush=True)
        return added


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pbf',default='data/raw/finland.osm.pbf')
    parser.add_argument('--cache',default='data/cache/finland.db')
    args=parser.parse_args()
    extend(args.pbf,args.cache)
