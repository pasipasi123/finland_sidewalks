import test from 'node:test';
import assert from 'node:assert/strict';
import {cohortRows,queryRows,valueFor,validateDataset} from '../web/data-model.js';
import {messages} from '../web/i18n.js';
const row=(code,name,km,perCapita,population=1000)=>({code,name,population,total_km:km,m_per_resident:perCapita,
  km:{tagged:0,footway:km,shared:100-km,segregated:0,unknown:1},shared_m_per_resident:100-km,segregated_m_per_resident:0,unknown_m_per_resident:1});
test('Numeric sorting uses numbers, all four columns and both directions',()=>{
 const rows=[row('001','Beta',9,9,900),row('002','Alpha',100,1,10000),row('003','Gamma',20,20,2000)];
 assert.deepEqual(queryRows(rows,{sortKey:'km'}).map(r=>r.code),['002','003','001']);
 assert.deepEqual(queryRows(rows,{sortKey:'km',direction:'asc'}).map(r=>r.code),['001','003','002']);
 assert.equal(queryRows(rows,{sortKey:'population'})[0].code,'002');
 assert.equal(queryRows(rows)[0].code,'003');
 assert.deepEqual(queryRows(rows,{sortKey:'name',direction:'asc'}).map(r=>r.name),['Alpha','Beta','Gamma']);
 assert.equal(rows[0].code,'001');
});
test('Municipal search supports accents, alternate names and codes',()=>{
 const rows=[row('992','Äänekoski',1,1),{...row('478','Mariehamn',2,2),name_aliases:['Maarianhamina - Mariehamn']}];
 assert.equal(queryRows(rows,{query:'  aanekoski '})[0].name,'Äänekoski');
 assert.equal(queryRows(rows,{query:'maarianhamina'})[0].code,'478');
 assert.equal(queryRows(rows,{query:'478'})[0].name,'Mariehamn');
 assert.equal(queryRows(rows,{query:'does-not-exist'}).length,0);
});
test('Every type uses its own precomputed kilometre and per-capita field',()=>{
 const r=row('001','Alpha',9,9);
 assert.equal(valueFor(r,'sidewalks','km'),9);
 assert.equal(valueFor(r,'shared','km'),91);
 assert.equal(valueFor(r,'shared','perCapita'),91);
 assert.equal(valueFor(r,'segregated','km'),0);
 assert.equal(valueFor(r,'unknown','perCapita'),1);
});
test('Comma-separated search preserves group ranks and does not duplicate matches',()=>{
 const rows=[row('001','Oulu',9,9),row('002','Vantaa',20,20),row('003','Helsinki',100,100)];
 assert.deepEqual(queryRows(rows,{query:'oulu, VANTAA'}).map(r=>[r.name,r.position]),[['Vantaa',2],['Oulu',3]]);
 assert.equal(queryRows(rows,{query:'Oulu, oulu, 001'}).length,1);
 assert.equal(queryRows(rows,{query:', ,'}).length,3);
});
test('Population classes have explicit non-overlapping boundaries and local ranks',()=>{
 const rows=[row('001','A',1,1,19999),row('002','B',2,2,20000),row('003','C',3,3,99999),row('004','D',4,4,100000)];
 assert.deepEqual(cohortRows(rows,'small').map(r=>r.code),['001']);
 assert.deepEqual(cohortRows(rows,'medium').map(r=>r.code),['002','003']);
 assert.deepEqual(cohortRows(rows,'large').map(r=>r.code),['004']);
 assert.equal(queryRows(rows,{sizeClass:'medium',query:'B'})[0].position,2);
 assert.equal(queryRows(rows,{sizeClass:'large',query:'D'})[0].position,1);
 assert.equal(queryRows(rows,{sizeClass:'small',query:'D'}).length,0);
});
test('Equal indicator values share a rank, including after a name search',()=>{
 const rows=[row('001','A',10,10),row('002','B',10,10),row('003','C',1,1)];
 assert.deepEqual(queryRows(rows).map(r=>r.position),[1,1,3]);
 assert.equal(queryRows(rows,{query:'B'})[0].position,1);
 assert.deepEqual(queryRows(rows,{direction:'asc'}).map(r=>r.position),[1,2,2]);
});
test('Zero is a result; missing data and demo data are not results',()=>{
 const r=row('001','Alpha',0,0), data={demo:false,coverage_count:1,municipalities:[r],osm:{osm_date:'2026-11-05'},population_date:'2025-12-31',method_version:'1.6.5'};
 assert.equal(validateDataset(data),data);
 assert.throws(()=>validateDataset({...data,demo:true}));
 assert.throws(()=>validateDataset({...data,coverage_count:2}));
 assert.throws(()=>validateDataset({...data,method_version:'1.0.0<script>'}));
 assert.throws(()=>validateDataset({...data,coverage_count:2,municipalities:[r,r]}));
 const missing=structuredClone(data);delete missing.municipalities[0].unknown_m_per_resident;
 assert.throws(()=>validateDataset(missing));
});
test('Finnish and English cover the same controls and content',()=>{
 assert.deepEqual(Object.keys(messages.fi).sort(),Object.keys(messages.en).sort());
 assert.deepEqual(Object.keys(messages.fi.descriptions).sort(),Object.keys(messages.en.descriptions).sort());
 for(const language of ['fi','en']) assert.ok(messages[language].legalBody.includes('https://www.finlex.fi/fi/lainsaadanto/2018/729'));
});
