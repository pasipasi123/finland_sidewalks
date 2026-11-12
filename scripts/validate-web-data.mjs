import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {validateDataset,TYPES,valueFor,queryRows} from '../web/data-model.js';
const data=validateDataset(JSON.parse(await readFile('web/data/municipalities.json','utf8')));
assert.equal(data.coverage_count,308,'All 308 municipalities must be calculated before deployment');
assert.equal(data.expected_count,308);
assert.ok(data.osm.osm_date && data.osm.sha256 && data.population_date && data.population_source && data.signature);
assert.equal(data.license,'ODbL-1.0');
assert.equal(data.population_license,'CC-BY-4.0');
const populationLines=(await readFile('data/population-finland.csv','utf8')).trim().split(/\r?\n/);
assert.equal(populationLines.shift(),'code,population,date,source');
const populations=new Map(populationLines.map(line=>{
 const parts=line.split(',');assert.equal(parts.length,4);return [parts[0],parts];
}));
assert.deepEqual([...populations.keys()].sort(),data.municipalities.map(row=>row.code).sort());
for(const row of data.municipalities){
 const population=populations.get(row.code);
 assert.equal(row.population,Number(population[1]));
 assert.equal(data.population_date,population[2]);
 assert.equal(data.population_source,population[3]);
 assert.ok(!row.geometry && !row.map_path,'The table payload should not carry geometries');
 assert.ok(Math.abs(row.total_km-row.km.tagged-row.km.footway-row.km.segregated)<0.000002);
 for(const type of Object.keys(TYPES)) assert.ok(Math.abs(valueFor(row,type,'km')*1000/row.population-valueFor(row,type,'perCapita'))<=0.000051,`${row.code} ${type}: invalid per-capita figure`);
}
const csv=await readFile('web/data/municipalities.csv','utf8');
for(const type of Object.keys(TYPES)){
 for(const row of queryRows(data.municipalities,{type})) assert.equal(row['rank_'+TYPES[type].perCapita],row.position);
}
for(const row of queryRows(data.municipalities,{sortKey:'km'})) assert.equal(row.rank_total_km,row.position);
assert.equal(csv.trim().split(/\r?\n/).length,309);
assert.ok(csv.includes('unknown_m_per_resident') && csv.includes('population_source'));
console.log(`Validated ${data.coverage_count} municipalities, all path types, precomputed figures and CSV.`);
