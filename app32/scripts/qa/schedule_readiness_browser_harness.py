"""Local-only schedule readiness fixture: no persistence or financial writes."""
import time
from flask import render_template,request,jsonify
from direct_entry_browser_harness import app
state={'attempts':0}
@app.get('/schedule-fixture')
def schedule_fixture():
 state['attempts']=1 if request.args.get('detail') else 0
 return render_template('modules/financial/schedules.html',company_id=9,schedule_id=1 if request.args.get('detail') else None,initial_entry_type='receivable',schedule=None)
@app.get('/api/financial/schedules/options')
def schedule_options():
 state['attempts']+=1
 time.sleep(5)
 if state['attempts']==1:return jsonify(error='Falha sintética de catálogo'),503
 return jsonify(counterparties=[],bank_accounts=[],chart_accounts=[],cost_centers=[],correction_indexes=[],discount_rules=[],enabled_domains=[],default_suggestions={},budget_versions=[],budget_lines=[],budget_contracts=[],budget_documents=[])
@app.get('/api/financial/schedules/1')
def detail():
 return jsonify(id=1,schedule_code='SINTETICO',status='active',entry_type='receivable',description='Somente teste',template_amount=10,frequency='one_time',allocations=[],related_entries=[],attachments=[],is_bordero_locked=True,bordero={'code':'TESTE'})
@app.get('/api/financial/schedules/1/calculation-logs')
def logs():return jsonify(logs=[])
if __name__=='__main__':app.run(host='127.0.0.1',port=5092,threaded=True,use_reloader=False)
