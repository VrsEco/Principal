"""Local-only readiness fixture. No database or mutation endpoints."""
import time
from flask import render_template, request, jsonify
from direct_entry_browser_harness import app

attempts = {'schedules': 0}
@app.get('/bordero-fixture')
def bordero_page():
    attempts['schedules'] = 0
    return render_template('modules/financial/borderos.html', company_id=9,
                           bordero_id=None, initial_bordero_type='receivable')

@app.get('/api/financial/schedules')
def schedules():
    attempts['schedules'] += 1
    time.sleep(3)
    if attempts['schedules'] == 1:
        return jsonify(error='Falha sintética de leitura'), 503
    return jsonify([])

@app.get('/api/financial/catalogs/bank_accounts')
def banks():
    time.sleep(6)
    return jsonify([])

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5090, threaded=True, use_reloader=False)
