"""Update feature rows in an existing GeoPackage without replacing its file/layers."""
import argparse
import sqlite3
import struct
from contextlib import closing
from functools import lru_cache
from pathlib import Path

from shapely import from_wkb

def quote(name):
    return '"' + name.replace('"','""') + '"'

def geometry_functions(db):
    @lru_cache(maxsize=2048)
    def decoded(blob):
        if blob is None:
            return None
        if blob[:2] != b'GP':
            raise ValueError('Not a GeoPackage geometry')
        envelope = (blob[3] >> 1) & 7
        size = {0:0,1:32,2:48,3:48,4:64}[envelope]
        return from_wkb(blob[8+size:])

    db.create_function('ST_IsEmpty',1,lambda blob:1 if blob is None or decoded(blob).is_empty else 0)
    for name,index in [('ST_MinX',0),('ST_MinY',1),('ST_MaxX',2),('ST_MaxY',3)]:
        db.create_function(name,1,lambda blob,index=index:None if blob is None else decoded(blob).bounds[index])
    db.create_function('ST_SRID',1,lambda blob:struct.unpack('<i' if blob[3]&1 else '>i',blob[4:8])[0] if blob else None)
    db.create_function('ST_GeometryType',1,lambda blob:decoded(blob).geom_type.upper() if blob else None)

def sync_gpkg(staged_path,target_path,backup_path=None):
    staged,target = Path(staged_path).resolve(),Path(target_path).resolve()
    if staged==target or not staged.is_file() or not target.is_file():
        raise ValueError('Staged and target must be distinct existing GeoPackages')
    inode = target.stat().st_ino
    with closing(sqlite3.connect(target,timeout=15)) as db:
        geometry_functions(db)
        db.execute('PRAGMA busy_timeout=15000')
        if backup_path:
            backup = Path(backup_path)
            if backup.exists():
                raise ValueError('Backup already exists; choose another filename')
            backup.parent.mkdir(parents=True,exist_ok=True)
            with closing(sqlite3.connect(backup)) as snapshot:
                db.backup(snapshot)
        db.execute('ATTACH DATABASE ? AS incoming',(str(staged),))
        tables = db.execute("SELECT table_name,data_type FROM incoming.gpkg_contents WHERE data_type IN ('features','attributes')").fetchall()
        manifest = {}
        try:
            db.execute('BEGIN IMMEDIATE')
            for table,kind in tables:
                if not db.execute('SELECT 1 FROM main.gpkg_contents WHERE table_name=?',(table,)).fetchone():
                    raise ValueError(f'Target layer does not exist: {table}')
                source_columns = db.execute(f'PRAGMA incoming.table_info({quote(table)})').fetchall()
                existing = {r[1] for r in db.execute(f'PRAGMA main.table_info({quote(table)})')}
                for _,name,data_type,_,_,_ in source_columns:
                    if name not in existing:
                        db.execute(f'ALTER TABLE main.{quote(table)} ADD COLUMN {quote(name)} {data_type}')
                columns = ','.join(quote(row[1]) for row in source_columns)
                db.execute(f'DELETE FROM main.{quote(table)}')
                db.execute(f'INSERT INTO main.{quote(table)} ({columns}) SELECT {columns} FROM incoming.{quote(table)}')
                count = db.execute(f'SELECT COUNT(*) FROM main.{quote(table)}').fetchone()[0]
                expected = db.execute(f'SELECT COUNT(*) FROM incoming.{quote(table)}').fetchone()[0]
                if count!=expected:
                    raise ValueError(f'Count mismatch: {table}')
                if kind=='features':
                    source_geom = db.execute('SELECT column_name,geometry_type_name,srs_id FROM incoming.gpkg_geometry_columns WHERE table_name=?',(table,)).fetchone()
                    target_geom = db.execute('SELECT column_name,geometry_type_name,srs_id FROM main.gpkg_geometry_columns WHERE table_name=?',(table,)).fetchone()
                    if source_geom!=target_geom:
                        raise ValueError(f'Geometry schema mismatch: {table}')
                    rtree = f'rtree_{table}_{target_geom[0]}'
                    if db.execute(f'SELECT COUNT(*) FROM {quote(rtree)}').fetchone()[0]!=count:
                        raise ValueError(f'Spatial index mismatch: {table}')
                    if db.execute("SELECT 1 FROM sqlite_master WHERE name='gpkg_ogr_contents'").fetchone():
                        db.execute('UPDATE gpkg_ogr_contents SET feature_count=? WHERE table_name=?',(count,table))
                metadata = db.execute('SELECT last_change,min_x,min_y,max_x,max_y,description FROM incoming.gpkg_contents WHERE table_name=?',(table,)).fetchone()
                db.execute('UPDATE main.gpkg_contents SET last_change=?,min_x=?,min_y=?,max_x=?,max_y=?,description=? WHERE table_name=?',(*metadata,table))
                manifest[table] = count
                print(f'{table}: {count:,} riviä päivitetty',flush=True)
            if db.execute('PRAGMA main.integrity_check').fetchone()[0]!='ok':
                raise ValueError('Integrity check failed')
            if db.execute('PRAGMA main.foreign_key_check').fetchall():
                raise ValueError('Foreign key check failed')
            db.commit()
        except Exception:
            db.rollback()
            raise
    if target.stat().st_ino!=inode:
        raise ValueError('File identity unexpectedly changed')
    print(f'Päivitetty sama tiedosto: {target}',flush=True)
    return manifest

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged',required=True)
    parser.add_argument('--target',required=True)
    parser.add_argument('--backup')
    args = parser.parse_args()
    sync_gpkg(args.staged,args.target,args.backup)

if __name__=='__main__':
    main()
