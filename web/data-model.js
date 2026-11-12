export const TYPES = {
  sidewalks: { km: 'total_km', perCapita: 'm_per_resident' },
  shared: { km: 'shared', perCapita: 'shared_m_per_resident' },
  segregated: { km: 'segregated', perCapita: 'segregated_m_per_resident' },
  unknown: { km: 'unknown', perCapita: 'unknown_m_per_resident' },
};
export const SORT_KEYS = ['name', 'km', 'perCapita', 'population'];
export const SIZE_CLASSES = {all:[0,Infinity],large:[100000,Infinity],medium:[20000,100000],small:[0,20000]};
export const normalize = value => String(value).normalize('NFD').replace(/\p{M}/gu, '').toLocaleLowerCase('fi');
export function cohortRows(rows,sizeClass='all') {
  const [minimum,maximum]=SIZE_CLASSES[sizeClass] || SIZE_CLASSES.all;
  return rows.filter(row=>row.population>=minimum && row.population<maximum);
}
export function valueFor(row, type, column) {
  if (column === 'name' || column === 'population') return row[column];
  if (column === 'perCapita') return row[TYPES[type].perCapita];
  return type === 'sidewalks' ? row.total_km : row.km[TYPES[type].km];
}
export function queryRows(rows, {query='', type='sidewalks', sortKey='perCapita', direction='desc', lang='fi',sizeClass='all'}={}) {
  const terms=query.split(',').map(term=>normalize(term.trim())).filter(Boolean);
  const collator=new Intl.Collator(lang, {sensitivity:'base',numeric:true});
  const sorted=cohortRows(rows,sizeClass).sort((a,b)=>{
    const av=valueFor(a,type,sortKey), bv=valueFor(b,type,sortKey);
    const difference=sortKey==='name' ? collator.compare(av,bv) : av-bv;
    return (direction==='asc' ? difference : -difference) || collator.compare(a.name,b.name) || a.code.localeCompare(b.code);
  });
  let previous,position=0;
  // Rank the full comparison group before applying the name search.
  return sorted.map((row,index)=>{
    const value=valueFor(row,type,sortKey);
    if(index===0 || value!==previous) position=index+1;
    previous=value;
    return {...row,position};
  }).filter(row=>!terms.length || terms.some(term=>normalize([row.name,row.code,...(row.name_aliases || [])].join(' ')).includes(term)));
}
export function validateDataset(data) {
  if(data.demo || !Array.isArray(data.municipalities) || !data.municipalities.length || data.coverage_count!==data.municipalities.length) throw Error('Invalid coverage');
  if(!data.osm?.osm_date || !data.population_date || !/^\d+\.\d+\.\d+$/.test(data.method_version)) throw Error('Missing data provenance');
  const codes=new Set();
  for(const row of data.municipalities) {
    if(!/^\d{3}$/.test(row.code) || codes.has(row.code) || typeof row.name!=='string' || !row.name || !Number.isSafeInteger(row.population) || row.population<=0) throw Error('Invalid municipality');
    codes.add(row.code);
    for(const type of Object.keys(TYPES)) for(const column of ['km','perCapita']) {
      const value=valueFor(row,type,column);
      if(!Number.isFinite(value) || value<0) throw Error('Missing precomputed indicator');
    }
  }
  return data;
}
