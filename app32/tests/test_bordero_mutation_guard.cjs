// No network: exercise actual production functions with a synthetic fetch.
const assert = require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../static/js/financial_borderos.js'),'utf8');
const controls=source.slice(source.indexOf('  let initializationPending = false;'),source.indexOf('  function init() {'));
const fetchCode=source.slice(source.indexOf('  async function fetchJson('),source.indexOf('  function formatCurrencyFromDigits('));
function fixture(fetch){
 const status={textContent:''}, guard={inert:false,disabled:true,setAttribute(k,v){this[k]=v;}};
 const ctx={fetch,document:{querySelectorAll:()=>[guard]},$:()=>status};
 vm.createContext(ctx);vm.runInContext(controls+'\n'+fetchCode+'\ndataReady=true;',ctx);
 return {ctx,status,guard};
}
const ok=()=>({ok:true,json:async()=>({id:1})});
async function main(){
 let finish,calls=0;
 const f=fixture(()=>{calls++;return new Promise(r=>finish=r);});
 const action=()=>f.ctx.fetchJson('/synthetic',{method:'POST'});
 const first=f.ctx.runFinancialAction(action);
 await f.ctx.runFinancialAction(action);assert.equal(calls,1);assert.equal(f.guard.inert,true);
 finish(ok());await first;assert.equal(f.guard.inert,false);assert.equal(f.guard.disabled,true);
 assert.match(f.status.textContent,/concluída/);

 const validation=fixture(()=>{throw Error('must not call');});
 await validation.ctx.runFinancialAction(()=>{throw Error('Dados inválidos');});
 assert.equal(validation.guard.inert,false);assert.match(validation.status.textContent,/inválidos/);
 await validation.ctx.runFinancialAction(async()=>{});assert.equal(validation.guard.inert,false);

 let unknownCalls=0;
 const unknown=fixture(async()=>{unknownCalls++;throw Error('connection lost');});
 const write=()=>unknown.ctx.fetchJson('/synthetic',{method:'POST'});
 await unknown.ctx.runFinancialAction(write);await unknown.ctx.runFinancialAction(write);
 assert.equal(unknownCalls,1);assert.equal(unknown.guard.inert,true);
 assert.match(unknown.status.textContent,/Não foi possível confirmar/);
 await unknown.ctx.initializeData();assert.equal(unknown.guard.inert,true);

 const refresh=fixture(async()=>ok());
 await refresh.ctx.runFinancialAction(async()=>{
   await refresh.ctx.fetchJson('/synthetic',{method:'PUT'});
   assert.match(refresh.status.textContent,/Gravação confirmada/);
   throw Error('refresh failed');
 });
 assert.equal(refresh.guard.inert,true);assert.match(refresh.status.textContent,/atualização da tela falhou/);
 const invalidJson=fixture(async()=>({ok:true,json:async()=>{throw Error('bad json');}}));
 await invalidJson.ctx.runFinancialAction(()=>invalidJson.ctx.fetchJson('/synthetic',{method:'POST'}));
 assert.equal(invalidJson.guard.inert,true);assert.match(invalidJson.status.textContent,/Gravação confirmada/);
 const rejected=fixture(async()=>({ok:false,json:async()=>({error:'denied'})}));
 await rejected.ctx.runFinancialAction(()=>rejected.ctx.fetchJson('/synthetic',{method:'DELETE'}));
 assert.equal(rejected.guard.inert,true);assert.match(rejected.status.textContent,/Não foi possível confirmar/);
 const redirect=fixture(async()=>ok());
 await redirect.ctx.runFinancialAction(async()=>{await redirect.ctx.fetchJson('/synthetic',{method:'POST'});vm.runInContext('mutation.redirecting=true',redirect.ctx);});
 assert.equal(redirect.guard.inert,true);
 console.log('PASS: one write on double click; validation/cancel; uncertain response; confirmed write with failed refresh/JSON; HTTP rejection; redirect lock; disabled preserved');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
