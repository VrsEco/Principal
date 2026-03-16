from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "app = create_app()\n"
    "targets = ['agent', 'meeting', 'user', 'indicator', 'incentive']\n"
    "for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):\n"
    "    endpoint = rule.endpoint.lower()\n"
    "    rule_s = rule.rule.lower()\n"
    "    if any(t in endpoint or t in rule_s for t in targets):\n"
    "        print('RULE::{}::{}'.format(rule.rule, rule.endpoint))\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
