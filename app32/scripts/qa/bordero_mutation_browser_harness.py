"""Synthetic mutations only. No DB, external service, or persistent financial data."""
import time
from flask import render_template, request, jsonify
from direct_entry_browser_harness import app
state={'writes':0,'mode':'success'}
record=dict(id=1,bordero_type='receivable',bordero_code='TESTE',name='Somente simulacao local',status='open',open_amount=10,total_amount=10,items=[],settlements=[],can_delete=False)
@app.get('/mutation-fixture')
def mutation_page():
 state.update(writes=0,mode=request.args.get('mode','success'))
 return '<p>SIMULACAO LOCAL — sem banco. <a href="/fixture-metrics">Contador de envios sintéticos</a></p>'+render_template('modules/financial/borderos.html',company_id=9,bordero_id=1,initial_bordero_type='receivable')
@app.get('/fixture-metrics')
def metrics():return jsonify(state)
@app.get('/api/financial/schedules')
def schedules():return jsonify([])
@app.get('/api/financial/catalogs/bank_accounts')
def banks():return jsonify([])
@app.route('/api/financial/borderos/1',methods=['GET','PUT'])
def detail():
 if request.method=='PUT':
  state['writes']+=1;time.sleep(4)
  if state['mode']=='uncertain':return jsonify(error='Resposta sintética inconclusiva'),503
  return jsonify(record)
 if state['mode']=='refresh-failure' and state['writes']:return jsonify(error='Falha sintética de releitura'),503
 return jsonify(record)
@app.post('/api/financial/borderos/1/settlements')
def settlement():
 state['writes']+=1;time.sleep(4)
 return jsonify(id=999)
if __name__=='__main__':app.run(host='127.0.0.1',port=5091,threaded=True,use_reloader=False)
