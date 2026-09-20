from pathlib import Path
import sys,time
from flask import Flask,render_template,request,jsonify,send_from_directory
from jinja2 import ChoiceLoader,DictLoader,FileSystemLoader
ROOT=Path(__file__).resolve().parents[2]
app=Flask(__name__,static_folder=str(ROOT/'static'))
# Mirror the deployed asset topology without copying or changing runtime files.
original_send_static = app.send_static_file
def send_fixture_static(filename):
 if filename == 'js/date_utils.js':
  return send_from_directory(str(ROOT.parent/'static'), filename)
 return original_send_static(filename)
app.send_static_file = send_fixture_static
app.secret_key='local-synthetic-only' 
app.url_build_error_handlers.append(lambda error, endpoint, values: '/fixture-unavailable')
app.jinja_loader=FileSystemLoader(str(ROOT/'templates'))
app.jinja_env.globals.update(has_permission=lambda *a: False, is_platform_admin=lambda: False, current_user={'name':'Teste local'})
app.add_url_rule('/profile', endpoint='auth.profile', view_func=lambda: 'Local only')
app.jinja_env.globals['static_asset_version']=lambda name:'local-test'
@app.get('/')
def page():
 return render_template('modules/financial/entry_direct.html',company_id=9,initial_entry_type=request.args.get('entry_type','receivable'))
@app.get('/api/financial/entries/direct/options')
def options():
 time.sleep(8)
 return jsonify(counterparties=[],bank_accounts=[],chart_accounts=[],cost_centers=[],correction_indexes=[],discount_rules=[],enabled_domains=[],default_suggestions={})
if __name__=='__main__':app.run(host='127.0.0.1',port=5087,threaded=True,use_reloader=False)


