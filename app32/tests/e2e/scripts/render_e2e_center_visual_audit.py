from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from string import Template
from types import SimpleNamespace

ROOT_DIR = Path(__file__).resolve().parents[4]
APP_PACKAGE_ROOT = ROOT_DIR / 'app32'
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(APP_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_PACKAGE_ROOT))

from services.e2e_operations_center_service import E2EOperationsCenterService


HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang='pt-BR'>
<head>
  <meta charset='utf-8'>
  <title>Visual Audit - Central E2E</title>
  <style>
    body { font-family: Arial, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:24px; }
    .hero, .card { background:#111827; border:1px solid #334155; border-radius:18px; padding:20px; margin-bottom:16px; }
    .grid { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:16px; }
    .stat { background:#1e293b; border-radius:14px; padding:16px; }
    .stat strong { display:block; font-size:28px; margin-top:6px; }
    table { width:100%; border-collapse:collapse; }
    th, td { padding:10px; border-bottom:1px solid #334155; text-align:left; }
    th { color:#93c5fd; }
    .pill { display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:700; }
    .ok { background:#064e3b; color:#a7f3d0; }
    .ko { background:#7f1d1d; color:#fecaca; }
    code { color:#93c5fd; }
  </style>
</head>
<body>
  <section class='hero'>
    <h1>Central de Testes E2E — Auditoria Visual</h1>
    <p>Snapshot supervisionado da Sprint 6 para validar densidade visual, métricas e ações da central operacional.</p>
  </section>
  <section class='grid'>
    <div class='stat'><span>Execuções</span><strong>$total_runs</strong></div>
    <div class='stat'><span>Falhas</span><strong>$failed_runs</strong></div>
    <div class='stat'><span>Backlog</span><strong>$backlog_candidates</strong></div>
  </section>
  <section class='card'>
    <h2>Último diff</h2>
    <p>Status: <span class='pill $diff_class'>$diff_status</span></p>
    <p>Regressões: $regressions | Recuperadas: $recovered | Novas: $new_journeys</p>
  </section>
  <section class='card'>
    <h2>Últimas execuções</h2>
    <table>
      <thead><tr><th>Ambiente</th><th>Run</th><th>Status</th><th>Falhas</th><th>Artefatos</th></tr></thead>
      <tbody>$rows</tbody>
    </table>
  </section>
</body>
</html>""")


def main() -> int:
    output_root = ROOT_DIR / 'app32' / 'tests' / 'e2e' / 'outputs' / 'visual_audit' / datetime.now().strftime('run_%Y%m%d_%H%M%S')
    output_root.mkdir(parents=True, exist_ok=True)
    state = E2EOperationsCenterService.build_frontend_state(SimpleNamespace(id=9, name='Versus', client_code='VRS'))

    rows = []
    for run in state.get('latest_runs', [])[:8]:
        css = 'ko' if run.get('status') == 'failed' else 'ok'
        rows.append(
            f"<tr><td>{run.get('environment')}</td><td>{run.get('run_id')}</td><td><span class='pill {css}'>{run.get('status')}</span></td><td>{run.get('journeys_failed')}</td><td>{run.get('artifacts_total')}</td></tr>"
        )
    html = HTML_TEMPLATE.substitute(
        total_runs=state['summary']['total_runs'],
        failed_runs=state['summary']['failed_runs'],
        backlog_candidates=state['summary']['backlog_candidates'],
        diff_status=state['latest_diff']['status'],
        regressions=len(state['latest_diff'].get('regressions', [])),
        recovered=len(state['latest_diff'].get('recovered', [])),
        new_journeys=len(state['latest_diff'].get('new_journeys', [])),
        diff_class='ko' if state['latest_diff']['status'] == 'regression' else 'ok',
        rows=''.join(rows) or '<tr><td colspan="5">Sem dados</td></tr>',
    )

    html_path = output_root / 'e2e_center_visual_audit.html'
    html_path.write_text(html, encoding='utf-8')

    screenshot_path = output_root / 'e2e_center_visual_audit.png'
    screenshot_status = 'skipped'
    screenshot_error = None
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1800})
            page.goto(html_path.as_uri(), wait_until='load')
            page.screenshot(path=str(screenshot_path), full_page=True)
            browser.close()
        screenshot_status = 'generated'
    except Exception as exc:  # pragma: no cover
        screenshot_error = str(exc)

    metadata = {
        'html_path': str(html_path),
        'screenshot_path': str(screenshot_path),
        'screenshot_status': screenshot_status,
        'screenshot_error': screenshot_error,
        'summary': state['summary'],
        'latest_diff': state['latest_diff'],
    }
    (output_root / 'visual_audit.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
