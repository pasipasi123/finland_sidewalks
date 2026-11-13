import {TYPES,SORT_KEYS,SIZE_CLASSES,cohortRows,queryRows,valueFor,validateDataset} from './data-model.js';
import {messages} from './i18n.js?v=copy-4';

const $=selector=>document.querySelector(selector);
const readState=()=>{
  const params=new URLSearchParams(location.search);
  let saved;
  try { saved=localStorage.getItem('sidewalk-atlas-language'); } catch { /* Storage is optional. */ }
  return {lang:['fi','en'].includes(params.get('lang'))?params.get('lang'):(saved==='en'?'en':'fi'),
    type:Object.hasOwn(TYPES,params.get('type'))?params.get('type'):'sidewalks',
    sortKey:SORT_KEYS.includes(params.get('sort'))?params.get('sort'):'perCapita',
    direction:params.get('order')==='asc'?'asc':'desc',query:params.get('q') || '',
    sizeClass:Object.hasOwn(SIZE_CLASSES,params.get('size'))?params.get('size'):'all'};
};
let state=readState(), dataset, loadFailed=false;
$('#search').value=state.query;
$('#size-filter').value=state.sizeClass;
const number=(value,digits=0)=>new Intl.NumberFormat(state.lang==='fi'?'fi-FI':'en-GB',{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(value);
const date=value=>new Intl.DateTimeFormat(state.lang==='fi'?'fi-FI':'en-GB',{timeZone:'UTC'}).format(new Date(value));

function saveState(){
  const url=new URL(location.href);
  for(const key of ['lang','type','sort','order','q','size']) url.searchParams.delete(key);
  url.searchParams.set('lang',state.lang);
  if(state.type!=='sidewalks') url.searchParams.set('type',state.type);
  if(state.sortKey!=='perCapita') url.searchParams.set('sort',state.sortKey);
  if(state.direction!=='desc') url.searchParams.set('order',state.direction);
  if(state.query) url.searchParams.set('q',state.query);
  if(state.sizeClass!=='all') url.searchParams.set('size',state.sizeClass);
  history.replaceState(null,'',url);
}

function renderText(){
  const t=messages[state.lang];
  document.documentElement.lang=state.lang;
  document.title=t.pageTitle;
  // Only authored translation strings use HTML; municipality data uses textContent.
  document.querySelectorAll('[data-i18n]').forEach(element=>element.innerHTML=t[element.dataset.i18n]);
  document.querySelectorAll('[data-i18n-label]').forEach(element=>element.setAttribute('aria-label',t[element.dataset.i18nLabel]));
  document.querySelectorAll('[data-i18n-placeholder]').forEach(element=>element.setAttribute('placeholder',t[element.dataset.i18nPlaceholder]));
  $('.brand').setAttribute('aria-label',t.brand);
  document.querySelectorAll('[data-lang]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.lang===state.lang)));
  $('#table-caption').textContent=`${t[state.type]}: ${t.rowNumber}, ${t.length}, ${t.perCapita}, ${t.population}`;
  $('#table-panel').setAttribute('aria-labelledby',`tab-${state.type}`);
  $('#size-options').label=t.sizeGroup;
  document.querySelectorAll('[data-type]').forEach(button=>{
    const selected=button.dataset.type===state.type;
    button.setAttribute('aria-selected',String(selected));
    button.tabIndex=selected?0:-1;
  });
  if(dataset){
    const osm=date(dataset.osm.osm_date), pop=date(dataset.population_date);
    $('#coverage-number').textContent=number(dataset.coverage_count);
    $('#snapshot').textContent=t.snapshot(osm,pop);
    $('#method-version').textContent=t.version(dataset.method_version);
    $('#source-details').innerHTML=t.sourceBody(osm,pop,dataset.method_version);
  }else{
    $('#snapshot').textContent=t.loading;
  }
  if(loadFailed) $('#load-status').textContent=t.error;
}

function renderRows(){
  if(!dataset) return;
  const t=messages[state.lang], rows=queryRows(dataset.municipalities,state);
  const fragment=document.createDocumentFragment();
  for(const row of rows){
    const tr=document.createElement('tr');
    const ordinal=document.createElement('td');ordinal.className='row-number';ordinal.textContent=number(row.position);tr.append(ordinal);
    const name=document.createElement('td');name.className='municipality';name.setAttribute('role','rowheader');name.textContent=row.name;
    const code=document.createElement('small');code.textContent=' '+row.code;name.append(code);tr.append(name);
    for(const column of ['km','perCapita','population']){
      const td=document.createElement('td');td.className=`numeric${column==='perCapita'?' primary-number':''}`;
      td.textContent=number(valueFor(row,state.type,column),column==='population'?0:column==='km'?3:4);
      tr.append(td);
    }
    fragment.append(tr);
  }
  $('#rows').replaceChildren(fragment);
  $('#result-count').textContent=t.count(rows.length,cohortRows(dataset.municipalities,state.sizeClass).length);
  $('#empty').hidden=rows.length!==0;
  document.querySelectorAll('[data-column]').forEach(th=>{
    const key=th.dataset.column,active=key===state.sortKey;
    th.setAttribute('aria-sort',active?(state.direction==='asc'?'ascending':'descending'):'none');
    th.querySelector('.sort-icon').textContent=active?(state.direction==='asc'?'↑':'↓'):'↕';
    const column=t[{name:'municipality',km:'length',perCapita:'perCapita',population:'population'}[key]];
    const nextAscending=active?state.direction!=='asc':key==='name';
    th.querySelector('button').setAttribute('aria-label',t.sortAction(column,nextAscending));
  });
}
function render(){renderText();renderRows();}

$('#search').addEventListener('input',event=>{
  state.query=event.target.value;
  renderRows();saveState();$('.table-scroll').scrollTop=0;
});
$('#size-filter').addEventListener('change',event=>{
  state.sizeClass=event.target.value;renderRows();saveState();$('.table-scroll').scrollTop=0;
});
document.querySelectorAll('[data-sort]').forEach(button=>button.addEventListener('click',()=>{
  const next=button.dataset.sort;
  state.direction=state.sortKey===next?(state.direction==='asc'?'desc':'asc'):(next==='name'?'asc':'desc');
  state.sortKey=next;renderRows();saveState();$('.table-scroll').scrollTop=0;
}));
function selectType(type){state.type=type;render();saveState();$('.table-scroll').scrollTop=0;}
document.querySelectorAll('[data-type]').forEach(button=>{
  button.addEventListener('click',()=>selectType(button.dataset.type));
  button.addEventListener('keydown',event=>{
    const buttons=[...document.querySelectorAll('[data-type]')],index=buttons.indexOf(button);
    let target;
    if(event.key==='ArrowRight') target=buttons[(index+1)%buttons.length];
    if(event.key==='ArrowLeft') target=buttons[(index+buttons.length-1)%buttons.length];
    if(event.key==='Home') target=buttons[0];
    if(event.key==='End') target=buttons.at(-1);
    if(target){event.preventDefault();selectType(target.dataset.type);target.focus();}
  });
});
document.querySelectorAll('[data-lang]').forEach(button=>button.addEventListener('click',()=>{
  state.lang=button.dataset.lang;
  try{localStorage.setItem('sidewalk-atlas-language',state.lang);}catch{/* Optional. */}
  render();saveState();
}));
addEventListener('popstate',()=>{state=readState();$('#search').value=state.query;$('#size-filter').value=state.sizeClass;render();});
renderText();
try{
  const response=await fetch('./data/municipalities.json');
  if(!response.ok) throw Error(`HTTP ${response.status}`);
  dataset=validateDataset(await response.json());
  $('#load-status').hidden=true;
  render();
}catch(error){
  dataset=undefined;
  loadFailed=true;
  $('#load-status').hidden=false;
  $('#load-status').textContent=messages[state.lang].error;
  $('#load-status').classList.add('error');
  $('#load-status').setAttribute('role','alert');
  console.error('Sidewalk Atlas data error:',error);
}
