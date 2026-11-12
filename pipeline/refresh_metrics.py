"""Refresh scalar indicators without rerunning geometry or replacing open GeoPackages."""
import argparse
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .cli import dump
from .metrics import update_per_capita
from .sync_gpkg import geometry_functions


def refresh_gpkg(path, result):
    """Update only municipal attributes and result metadata in one transaction."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f'GeoPackage puuttuu: {path}')
    result = dict(result)
    update_per_capita(result)
    with closing(sqlite3.connect(path, timeout=15)) as db:
        geometry_functions(db)
        try:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT arvo FROM laskentatiedot WHERE avain='laskentatulos'").fetchone()
            previous = json.loads(row[0]) if row else {}
            # A shared signature alone cannot identify a municipality.
            for key in ('code', 'signature', 'km', 'total_km', 'population', 'population_date', 'population_source'):
                if previous.get(key) != result[key]:
                    raise ValueError(f'GeoPackage ja kuntatulos poikkeavat ({key}): {path}')
            if db.execute('SELECT koodi FROM kuntaraja').fetchall() != [(result['code'],)]:
                raise ValueError(f'GeoPackagen kuntaraja ei vastaa tulosta: {path}')
            columns = {row[1] for row in db.execute('PRAGMA table_info(kuntaraja)')}
            for column in ('yhdistetty_m_asukas', 'eroteltu_m_asukas'):
                if column not in columns:
                    db.execute(f'ALTER TABLE kuntaraja ADD COLUMN {column} REAL')
            db.execute('UPDATE kuntaraja SET m_asukas=?, yhdistetty_m_asukas=?, eroteltu_m_asukas=?',
                       (result['m_per_resident'], result['shared_m_per_resident'], result['segregated_m_per_resident']))
            # Preserve export-specific metadata; refresh only derived metrics.
            update_per_capita(previous)
            db.execute("UPDATE laskentatiedot SET arvo=? WHERE avain='laskentatulos'",
                       (json.dumps(previous, ensure_ascii=False),))
            db.execute("UPDATE gpkg_contents SET last_change=? WHERE table_name IN ('kuntaraja','laskentatiedot')",
                       (datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),))
            db.commit()
        except Exception:
            db.rollback()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', default='data/results')
    parser.add_argument('--gpkg', nargs='+', default=[], help='Nykyiset katselupaketit; varmuuskopioita ei päivitetä')
    args = parser.parse_args()
    results = {}
    for path in sorted(Path(args.results).glob('[0-9][0-9][0-9].json')):
        result = json.loads(path.read_text(encoding='utf-8'))
        if update_per_capita(result):
            dump(path, result)
        results[result['code']] = result
        print(f'{result["code"]} {result["name"]}: yhdistetty {result["shared_m_per_resident"]:.4f}, eroteltu {result["segregated_m_per_resident"]:.4f} m/asukas')
    if not results:
        raise ValueError('Laskettuja kuntia ei löydy')
    for path in args.gpkg:
        with closing(sqlite3.connect(f'file:{Path(path).resolve().as_posix()}?mode=ro', uri=True)) as db:
            row = db.execute("SELECT arvo FROM laskentatiedot WHERE avain='kuntakoodi'").fetchone()
        if not row or row[0] not in results:
            raise ValueError(f'GeoPackagen kuntatulosta ei löydy: {path}')
        refresh_gpkg(path, results[row[0]])
        print(f'Mittarit päivitetty samaan tiedostoon: {path}')


if __name__ == '__main__':
    main()
