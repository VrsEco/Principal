// Pure controller tests: execute the production initialization with synthetic reads.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/js/financial_borderos.js'), 'utf8');
const start = source.indexOf('  let initializationPending = false;');
const end = source.indexOf('  function init() {', start);
function fixture(bank, schedules, detail = async () => {}) {
  const guards = [{inert: true, setAttribute(k,v) {this[k]=v;}}];
  const status = {textContent:''}; const retry={hidden:true,classList:{add(){},remove(){}}};
  const counters={bank:0,schedules:0};
  const ctx={ document:{querySelectorAll:()=>guards}, $:id=>id==='bordero-load-status'?status:retry,
    loadBankAccounts:()=>{counters.bank++;return bank();}, loadSchedules:()=>{counters.schedules++;return schedules();},
    borderoId:1, loadDetail:detail, ensureCreatedDateValue(){},applyType(){},state:{selectedType:'receivable'}};
  vm.createContext(ctx);vm.runInContext(source.slice(start,end),ctx);
  return {ctx,guards,status,retry,counters};
}
async function main(){
  let release; const pending=new Promise(resolve=>release=resolve);
  const f=fixture(()=>pending,async()=>{});
  f.guards.push({inert:true,setAttribute(k,v){this[k]=v;}}); // sidebar parsed after script
  const first=f.ctx.initializeData(); await f.ctx.initializeData();
  assert.equal(f.guards[0].inert,true);assert.equal(f.retry.hidden,true);
  assert.equal(f.counters.bank,1);assert.equal(f.counters.schedules,1);
  release(); await first;assert.ok(f.guards.every(g=>g.inert===false));assert.match(f.status.textContent,/pronto/);

  let fail=true;let releaseSecond;
  const second=new Promise(resolve=>releaseSecond=resolve);
  const g=fixture(async()=>{if(fail)throw Error('synthetic');},()=>fail?second:Promise.resolve());
  const failed=g.ctx.initializeData();await Promise.resolve();
  assert.equal(g.retry.hidden,true); // the other request is still running
  releaseSecond();await failed;
  assert.equal(g.guards[0].inert,true);assert.equal(g.retry.hidden,false);
  fail=false;await g.ctx.initializeData();assert.equal(g.guards[0].inert,false);
  assert.equal(g.counters.bank,2);assert.equal(g.counters.schedules,2);

  const h=fixture(async()=>{},async()=>{},async()=>{throw Error('detail unavailable');});
  await h.ctx.initializeData();assert.equal(h.guards[0].inert,true);assert.equal(h.retry.hidden,false);
  assert.ok(!source.slice(start,end).includes("method: 'POST'"));
  console.log('PASS: delayed readiness, concurrent initialization guard, failed read, settled-before-retry, recovery and detail failure');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
