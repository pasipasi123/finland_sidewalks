"""Fetch annual official municipality populations from Statistics Finland 11ra."""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--codes', default='564', help='Pilkuin erotetut kuntakoodit tai all (raja-aineiston kunnat)')
parser.add_argument('--boundaries', default='data/cache/municipalities.geojson')
parser.add_argument('--output', default='data/population.csv')
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
codes = (sorted({f['properties']['code'] for f in json.loads(Path(args.boundaries).read_text(encoding='utf-8'))['features']})
         if args.codes == 'all' else sorted({c.strip().zfill(3) for c in args.codes.split(',')}))
missing = {'KU'+code for code in codes} - set(area['values'])
if missing or year not in year_variable['values']:
    raise ValueError(f'Väestöaineistosta puuttuvat kunnat/vuosi: {sorted(missing)}, {year}')
root = Path('data/raw')
root.mkdir(parents=True, exist_ok=True)
target = Path(args.output)
target.parent.mkdir(parents=True, exist_ok=True)
previous = {}
if target.exists():
    with target.open(encoding='utf-8-sig', newline='') as source:
        previous = {r['code']: r for r in csv.DictReader(source)}
query = {'query': [
        {'code': area['code'], 'selection': {'filter': 'item', 'values': ['KU'+code for code in codes]}},
        {'code': 'contentscode', 'selection': {'filter': 'item', 'values': ['vaerak-vaesto']}},
        {'code': year_variable['code'], 'selection': {'filter': 'item', 'values': [year]}}
    ], 'response': {'format': 'json-stat2'}}
response = requests.post(url, json=query, timeout=60)
response.raise_for_status()
result = response.json()
area_index = result['dimension'][area['code']]['category']['index']
if isinstance(area_index,list):
    area_index = {code:i for i,code in enumerate(area_index)}
if len(result['value']) != len(codes) or set(area_index) != {'KU'+code for code in codes}:
    raise ValueError('Unexpected dimensions in population response')
for code in codes:
    value = result['value'][area_index['KU'+code]]
    if value is None or int(value) <= 0:
        raise ValueError(f'Invalid population response for {code}')
    previous[code] = {'code': code, 'population': int(value), 'date': year+'-12-31', 'source': 'https://statfin.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__vaerak/11ra.px/'}
raw_name = codes[0] if len(codes)==1 else 'finland'
(root/f'population-{raw_name}-{year}.json').write_text(json.dumps({'api':url, 'retrieved_at':datetime.now(timezone.utc).isoformat(),'query':query, 'response':result}, ensure_ascii=False, indent=2), encoding='utf-8')
with target.open('w', encoding='utf-8', newline='') as output:
    writer = csv.DictWriter(output, fieldnames=['code','population','date','source'])
    writer.writeheader()
    writer.writerows(previous[c] for c in sorted(previous))
print(f'{len(codes)} väkilukua vuodelta {year}: {target}',flush=True)
