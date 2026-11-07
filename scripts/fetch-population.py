"""Fetch annual official municipality populations from Statistics Finland 11ra."""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--codes', default='564')
parser.add_argument('--year')
args = parser.parse_args()
url = 'https://pxdata.stat.fi/PxWeb/api/v1/fi/StatFin/vaerak/11ra.px'
metadata_response = requests.get(url, timeout=60)
metadata_response.raise_for_status()
metadata = metadata_response.json()
variables = metadata['variables']
area = next(v for v in variables if v['text'] == 'Alue')
year_variable = next(v for v in variables if v.get('time') or v['text'] == 'Vuosi')
year = args.year or max(year_variable['values'])
codes = [c.strip().zfill(3) for c in args.codes.split(',')]
root = Path('data/raw')
root.mkdir(parents=True, exist_ok=True)
target = Path('data/population.csv')
previous = {}
if target.exists():
    with target.open(encoding='utf-8-sig', newline='') as source:
        previous = {r['code']: r for r in csv.DictReader(source)}
for code in codes:
    query = {'query': [
        {'code': area['code'], 'selection': {'filter': 'item', 'values': ['KU'+code]}},
        {'code': 'contentscode', 'selection': {'filter': 'item', 'values': ['vaerak-vaesto']}},
        {'code': year_variable['code'], 'selection': {'filter': 'item', 'values': [year]}}
    ], 'response': {'format': 'json-stat2'}}
    response = requests.post(url, json=query, timeout=60)
    response.raise_for_status()
    result = response.json()
    values = result['value']
    if len(values) != 1 or values[0] is None or int(values[0]) <= 0:
        raise ValueError(f'Invalid population response for {code}')
    previous[code] = {'code': code, 'population': int(values[0]), 'date': year+'-12-31', 'source': 'https://statfin.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__vaerak/11ra.px/'}
    (root/f'population-{code}-{year}.json').write_text(json.dumps({'api':url, 'retrieved_at':datetime.now(timezone.utc).isoformat(),'query':query, 'response':result}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(previous[code], ensure_ascii=False), flush=True)
with target.open('w', encoding='utf-8', newline='') as output:
    writer = csv.DictWriter(output, fieldnames=['code','population','date','source'])
    writer.writeheader()
    writer.writerows(previous[c] for c in sorted(previous))
