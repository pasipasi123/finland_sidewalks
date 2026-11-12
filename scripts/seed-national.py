"""Reuse verified municipal results when only the population table's coverage expands."""
import argparse
import csv
import json
from pathlib import Path

from pipeline.cli import VERSION, calculation_signature, dump
from pipeline.metrics import update_per_capita

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',default='data/results')
parser.add_argument('--output',default='data/results/national')
parser.add_argument('--old-population',default='data/population.csv')
parser.add_argument('--population',default='data/population-finland.csv')
parser.add_argument('--boundaries',default='data/cache/municipalities.geojson')
args=parser.parse_args()
def population(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as file:
        return {row['code']:row for row in csv.DictReader(file)}
before,after=population(args.old_population),population(args.population)
boundaries={f['properties']['code']:f for f in json.loads(Path(args.boundaries).read_text(encoding='utf-8'))['features']}
for path in sorted(Path(args.source).glob('[0-9][0-9][0-9].json')):
    result=json.loads(path.read_text(encoding='utf-8'))
    code=result['code']
    if result['method_version']!=VERSION or before[code]!=after[code] or result['geometry']!=boundaries[code]['geometry']:
        raise ValueError(f'{code}: lähtötieto tai menetelmä muuttui; laske normaalisti')
    row=after[code]
    if (result['population'],result['population_date'],result['population_source'])!=(int(row['population']),row['date'],row['source']):
        raise ValueError(f'{code}: väestö ei vastaa tulosta')
    old_signature=calculation_signature(result['osm'],args.boundaries,args.old_population,result['distance_m'])
    if result['signature']!=old_signature:
        raise ValueError(f'{code}: vanha tarkiste ei täsmää')
    target=Path(args.output)/path.name
    if target.exists():
        raise ValueError(f'Tulos on jo olemassa: {target}')
    result['reused_from']={'signature':old_signature,'reason':'Unchanged municipality population and geometry; population table expanded nationally'}
    result['signature']=calculation_signature(result['osm'],args.boundaries,args.population,result['distance_m'])
    update_per_capita(result)
    dump(target,result)
    print(f'{code} {result["name"]}: varmennettu tulos uudelleenkäytetty',flush=True)
