const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const s=fs.readFileSync(path.join(__dirname,'../static/js/financial_schedules.js'),'utf8');
const code=s.slice(s.indexOf('  let scheduleInitializationPending = false;'),s.lastIndexOf("  document.addEventListener('DOMContentLoaded', () => {"));
function fixture(overrides={}){
 const status={textContent:''},retry={hidden:true,classList:{add(){},remove(){}}},guards=[{inert:true,setAttribute(k,v){this[k]=v;}}],calls=[];
 const ctx={$:id=>id==='schedule-load-status'?status:retry,document:{querySelectorAll:()=>guards},
 loadOptions:async()=>{calls.push('options');},isFormMode:true,initialScheduleId:0,initialEntryType:'receivable',autoOpenSettlement:false,selectedSchedule:{id:1},
 loadSchedules:async()=>{calls.push('list');},openSettlementCompositionModal:async()=>{calls.push('modal');},updateFinancialTotals(){},alert(){throw Error('unexpected alert');},
 window:{selectSchedule:async()=>{calls.push('detail');},startNewSchedule:type=>calls.push(type),toggleRepeatFields(){},closeSettlementCompositionModal(){calls.push('close');}},...overrides};
 vm.createContext(ctx);vm.runInContext(code,ctx);return {ctx,status,retry,guards,calls};
}
async function main(){
 let release;const delayed=new Promise(r=>release=r);const f=fixture({loadOptions:()=>delayed});
 const pending=f.ctx.initializeSchedulePage();await f.ctx.initializeSchedulePage();assert.equal(f.guards[0].inert,true);release();await pending;
 assert.deepEqual(f.calls,['receivable']);assert.equal(f.guards[0].inert,false);
 const d=fixture({initialScheduleId:1});await d.ctx.initializeSchedulePage();assert.deepEqual(d.calls,['options','detail']);
 const l=fixture({isFormMode:false});await l.ctx.initializeSchedulePage();assert.deepEqual(l.calls,['options','list']);
 let fail=true;const e=fixture({loadOptions:async()=>{if(fail)throw Error('synthetic');}});await e.ctx.initializeSchedulePage();assert.equal(e.guards[0].inert,true);assert.equal(e.retry.hidden,false);fail=false;await e.ctx.initializeSchedulePage();assert.equal(e.guards[0].inert,false);assert.equal(e.retry.hidden,true);
 const m=fixture({initialScheduleId:1,autoOpenSettlement:true,openSettlementCompositionModal:async()=>{throw Error('simulation');}});await m.ctx.initializeSchedulePage();assert.equal(m.guards[0].inert,true);assert.ok(m.calls.includes('close'));assert.equal(m.retry.hidden,false);
 console.log('PASS: delayed new title, concurrent init guard, detail, legacy list, failed load/retry, failed automatic simulation closes modal');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
