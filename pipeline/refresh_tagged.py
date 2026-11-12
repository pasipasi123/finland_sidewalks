"""Upgrade 1.6.4 road-tag deduplication using unchanged accepted path geometries."""
import argparse
import filecmp
import json
import shutil
import sqlite3
import struct
import time
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from shapely import from_wkb, to_wkb
from shapely.geometry import mapping, shape

from .cli import VERSION, TO_METRES, TO_LONLAT, calculation_signature, dump, level, transform
from .export_gpkg import line_geometry, properties
from .metrics import update_per_capita
from .rules import category
from .sync_gpkg import geometry_functions, quote
from .tagged import TAGGED_POLICY, tagged_sidewalks


def update_gpkg(path, previous, result, tagged, tags_by_id):
    """Replace road-tag rows and their summaries, retaining all other feature rows."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f'GeoPackage puuttuu: {path}')
    with closing(sqlite3.connect(path, timeout=15)) as db:
        geometry_functions(db)
        stored = json.loads(db.execute("SELECT arvo FROM laskentatiedot WHERE avain='laskentatulos'").fetchone()[0])
        for key in ('code','signature','km','population'):
            if stored[key] != previous[key]:
                raise ValueError(f'GeoPackage ei vastaa aiempaa kuntatulosta ({key}): {path}')
        backup = path.with_name(path.stem+'_before_v1_6_5.gpkg')
        if not backup.exists():
            with closing(sqlite3.connect(backup)) as snapshot:
                db.backup(snapshot)
        try:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM jalkakaytavat_ajoratatagit')
            per_way = Counter()
            bounds = []
            for feature in tagged:
                p = feature['properties']
                geom = line_geometry(transform(TO_METRES,shape(feature['geometry'])))
                props = {**properties(p['osm_id'],tags_by_id[p['osm_id']]),
                         'luokka':'tagged','mukana':1,'pituus_m':p['length_m'],
                         'puoli':p['side'],'geom_rooli':'ajoradan keskilinja'}
                columns = ','.join(quote(k) for k in ['geom',*props])
                placeholders = ','.join('?' for _ in range(len(props)+1))
                # Standard GeoPackage binary header: little endian, no envelope, EPSG:3067.
                blob = b'GP\x00\x01'+struct.pack('<i',3067)+to_wkb(geom)
                db.execute(f'INSERT INTO jalkakaytavat_ajoratatagit ({columns}) VALUES ({placeholders})',
                           (blob,*props.values()))
                per_way[p['osm_id']] += p['length_m']
                bounds.append(geom.bounds)
            db.executemany('UPDATE osm_ajoradat SET kadunvarsi_m=?,mukaan_m=?,audit_osumia=? WHERE fid=?',
                           [(per_way[oid],per_way[oid],int(per_way[oid]>0),fid)
                            for fid,oid,old_length,old_included,old_hit in db.execute('SELECT fid,osm_id,kadunvarsi_m,mukaan_m,audit_osumia FROM osm_ajoradat').fetchall()
                            if (old_length,old_included,old_hit) != (per_way[oid],per_way[oid],int(per_way[oid]>0))])
            columns = {row[1] for row in db.execute('PRAGMA table_info(kuntaraja)')}
            for column in ('yhdistetty_m_asukas','eroteltu_m_asukas'):
                if column not in columns:
                    db.execute(f'ALTER TABLE kuntaraja ADD COLUMN {column} REAL')
            db.execute('UPDATE kuntaraja SET jalkakaytavat_km=?,m_asukas=?,yhdistetty_m_asukas=?,eroteltu_m_asukas=?',
                       (result['total_km'],result['m_per_resident'],result['shared_m_per_resident'],result['segregated_m_per_resident']))
            db.execute("UPDATE laskentatiedot SET arvo=? WHERE avain='laskentatulos'",
                       (json.dumps({k:v for k,v in result.items() if k!='geometry'},ensure_ascii=False),))
            manifest = json.loads(db.execute("SELECT arvo FROM laskentatiedot WHERE avain='tasojen_kohdemaarat'").fetchone()[0])
            manifest['jalkakaytavat_ajoratatagit'] = len(tagged)
            db.execute("UPDATE laskentatiedot SET arvo=? WHERE avain='tasojen_kohdemaarat'",(json.dumps(manifest),))
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='gpkg_ogr_contents'").fetchone():
                db.execute("UPDATE gpkg_ogr_contents SET feature_count=? WHERE table_name='jalkakaytavat_ajoratatagit'",(len(tagged),))
            extent = (min(b[0] for b in bounds),min(b[1] for b in bounds),max(b[2] for b in bounds),max(b[3] for b in bounds)) if bounds else (None,)*4
            db.execute("UPDATE gpkg_contents SET min_x=?,min_y=?,max_x=?,max_y=? WHERE table_name='jalkakaytavat_ajoratatagit'",extent)
            db.execute("UPDATE gpkg_contents SET last_change=? WHERE table_name IN ('jalkakaytavat_ajoratatagit','osm_ajoradat','kuntaraja','laskentatiedot')",
                       (datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),))
            if db.execute('SELECT COUNT(*) FROM rtree_jalkakaytavat_ajoratatagit_geom').fetchone()[0] != len(tagged):
                raise ValueError('GeoPackagen sijainti-indeksin kohdemäärä ei täsmää')
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('GeoPackagen eheystarkistus epäonnistui')
            db.commit()
        except Exception:
            db.rollback()
            raise


def refresh(args):
    started = time.perf_counter()
    if VERSION != '1.6.5':
        raise ValueError('Nopea päivitys on rajattu siirtymään 1.6.4 -> 1.6.5')
    root = Path(args.results)
    result_path = root/f'{args.code}.json'
    previous = json.loads(result_path.read_text(encoding='utf-8'))
    if previous['method_version'] != '1.6.4':
        raise ValueError('Nopea päivitys on tarkoitettu vain menetelmän 1.6.4 tuloksille')
    with closing(sqlite3.connect(f'file:{Path(args.cache).resolve().as_posix()}?mode=ro',uri=True)) as db:
        meta = json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
        if meta != previous['osm'] or previous['signature'] != calculation_signature(meta,args.boundaries,args.population,previous['distance_m'],'1.6.4'):
            raise ValueError('Lähtötiedot eivät vastaa vanhaa laskentaa; tee normaali compute')
        boundary = transform(TO_METRES,shape(previous['geometry']))
        x1,y1,x2,y2 = boundary.buffer(previous['distance_m']+10).bounds
        rows = db.execute('SELECT w.id,w.tags,w.geom FROM ways w JOIN bounds b ON w.id=b.id WHERE b.maxx>=? AND b.minx<=? AND b.maxy>=? AND b.miny<=?',(x1,x2,y1,y2))
        ways = {oid:(json.loads(tags),from_wkb(geom)) for oid,tags,geom in rows}
    audit = json.loads((root/f'{args.code}.segments.geojson').read_text(encoding='utf-8'))
    separate = [f for f in audit['features'] if f['properties']['category'] != 'tagged']
    paths = [(transform(TO_METRES,shape(f['geometry'])),ways[f['properties']['osm_id']][0]) for f in separate]
    roads = [(oid,tags,geom) for oid,(tags,geom) in ways.items() if category(tags)=='road']
    tagged = []
    length = 0.0
    for oid,side,geom in tagged_sidewalks(roads,paths,boundary,previous['distance_m'],level):
        length += geom.length
        tagged.append({'type':'Feature','properties':{'osm_id':oid,'category':'tagged','side':side,'length_m':round(geom.length,3)},'geometry':mapping(transform(TO_LONLAT,geom))})
    result = {**previous, 'km':dict(previous['km']), 'diagnostics':dict(previous['diagnostics'])}
    result['km']['tagged'] = round(length/1000,6)
    result['total_km'] = round(sum(result['km'][k] for k in ('tagged','footway','segregated')),6)
    result.update(method_version=VERSION,tagged_policy=TAGGED_POLICY,
                  signature=calculation_signature(meta,args.boundaries,args.population,previous['distance_m']),
                  generated_at=datetime.now(timezone.utc).isoformat())
    result['diagnostics'].update(audit_features=len(separate)+len(tagged),tagged_refresh_seconds=round(time.perf_counter()-started,3),separate_geometry_method_version='1.6.4')
    update_per_capita(result)
    rejection_path = root/f'{args.code}.rejections.json'
    rejections = json.loads(rejection_path.read_text(encoding='utf-8'))
    if rejections['signature'] != previous['signature']:
        raise ValueError('Hylkäystiedot eivät vastaa vanhaa laskentaa')
    backup = root/'v1.6.4-before-tagged-dedup'
    backup.mkdir(exist_ok=True)
    for source in (result_path, root/f'{args.code}.segments.geojson', rejection_path):
        if (backup/source.name).exists():
            if not filecmp.cmp(source,backup/source.name,shallow=False):
                raise ValueError(f'Varmuuskopio poikkeaa nykyisestä aineistosta: {backup/source.name}')
        else:
            shutil.copy2(source,backup/source.name)
    if args.gpkg:
        update_gpkg(args.gpkg,previous,result,tagged,{oid:t for oid,(t,_) in ways.items()})
    audit['features'] = separate+tagged
    rejections['signature'] = result['signature']
    dump(root/f'{args.code}.segments.geojson',audit)
    dump(rejection_path,rejections)
    dump(result_path,result)
    print(f'{result["name"]}: ajoratatägit {previous["km"]["tagged"]:.6f} -> {result["km"]["tagged"]:.6f} km; erilliset geometriat ennallaan',flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code',required=True)
    parser.add_argument('--population',required=True)
    parser.add_argument('--results',default='data/results')
    parser.add_argument('--cache',default='data/cache/finland.db')
    parser.add_argument('--boundaries',default='data/cache/municipalities.geojson')
    parser.add_argument('--gpkg')
    args = parser.parse_args()
    args.code = args.code.zfill(3)
    refresh(args)


if __name__ == '__main__':
    main()
