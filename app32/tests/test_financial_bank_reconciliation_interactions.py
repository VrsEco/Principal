from pathlib import Path
import re

from playwright.sync_api import sync_playwright


TEMPLATE_PATH = Path(
    r"C:\GestaoVersus\app32\app32\templates\modules\financial\bank_reconciliation.html"
)


def _build_probe_html() -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    script_match = re.search(r"<script>([\s\S]*?)</script>", template)
    assert script_match, "Script inline da conciliação não encontrado."
    script = script_match.group(1)
    return f"""<!doctype html>
<html>
  <body>
    <form id="upload-form"></form>
    <select id="upload-bank-account"></select>
    <input id="upload-file" type="file">
    <input id="upload-batch-code">
    <select id="upload-source-type"></select>
    <div id="upload-status"></div>
    <button id="upload-submit-button"></button>
    <div class="recon-page" data-company-id="1"></div>
    <div id="workspace-panel"></div>
    <div id="workspace-panel-body"></div>
    <div id="workspace-title"></div>
    <div id="workspace-subtitle"></div>
    <div id="workspace-summary"></div>
    <div id="bank-filter-group"></div>
    <div id="bank-column-actions"></div>
    <div id="bank-rows-list"></div>
    <div id="system-rows-list"></div>
    <div id="open-title-rows-list"></div>
    <div id="workbench-panel"></div>
    <div id="hero-account-name"></div>
    <div id="hero-account-status"></div>
    <div id="hero-batch-code"></div>
    <div id="hero-batch-status"></div>
    <div id="recon-overview-stats"></div>
    <div id="recon-modal-backdrop"></div>
    <div id="recon-modal-kicker"></div>
    <div id="recon-modal-title"></div>
    <div id="recon-modal-body"></div>
    <select id="workspace-bank-account"></select>
    <select id="batch-select"></select>
    <input id="bank-date-from">
    <input id="bank-date-to">
    <input id="open-title-due-date-from">
    <input id="open-title-due-date-to">
    <input id="settlement-date-from">
    <input id="settlement-date-to">
    <input id="system-search">
    <input id="reconciliation-amount-filter">
    <select id="reconciliation-movement-filter"></select>
    <script>{script}</script>
  </body>
</html>"""


def test_system_rows_allow_multiple_selection_via_checkbox_and_card(tmp_path):
    html_path = tmp_path / "bank_reconciliation_probe.html"
    html_path.write_text(_build_probe_html(), encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.route(
            "**/*",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"items": []}',
            )
            if route.request.resource_type == "fetch"
            else route.continue_(),
        )
        page.goto(html_path.as_uri())
        page.evaluate(
            """
            state.workspace = {
              bank_account: { id: 10, name: 'Conta Teste' },
              selected_batch: { id: 20, batch_code: 'B1', source_type: 'ofx' },
              available_batches: [{ id: 20, batch_code: 'B1', source_type: 'ofx' }],
              bank_rows: [
                { id: 1, row_number: 1, description: 'Linha 1', amount: 60, movement_nature: 'credit', matches: { linked_entry_ids: [], confirmed_count: 0, suggested_count: 0 }, needs_manual_action: true },
                { id: 2, row_number: 2, description: 'Linha 2', amount: 40, movement_nature: 'credit', matches: { linked_entry_ids: [], confirmed_count: 0, suggested_count: 0 }, needs_manual_action: true }
              ],
              system_rows: [
                { id: 101, entry_code: 'E101', description: 'Entrada A', original_amount: 100, remaining_amount: 100, movement_nature: 'credit', linked_rows_count: 0, is_reconciled: false, match_mode: 'unmatched' },
                { id: 102, entry_code: 'E102', description: 'Entrada B', original_amount: 60, remaining_amount: 60, movement_nature: 'credit', linked_rows_count: 0, is_reconciled: false, match_mode: 'unmatched' },
                { id: 103, entry_code: 'E103', description: 'Entrada C', original_amount: 40, remaining_amount: 40, movement_nature: 'credit', linked_rows_count: 0, is_reconciled: false, match_mode: 'unmatched' }
              ],
              open_title_rows: [],
              summary: {},
            };
            state.activeRowId = 1;
            state.selectedBankRowIds = [1, 2];
            renderBankRows();
            renderSystemRows();
            renderWorkbench();
            """
        )

        page.locator('#system-rows-list input[type="checkbox"]').nth(0).click()
        page.locator("#system-rows-list article").nth(1).click()

        payload = page.evaluate(
            """
            ({
              selectedEntryIds: state.selectedEntryIds.slice(),
              selectedBankRowIds: state.selectedBankRowIds.slice(),
            })
            """
        )
        browser.close()

    assert payload["selectedEntryIds"] == [101, 102]
    assert payload["selectedBankRowIds"] == [1, 2]


def test_bank_rows_render_all_items_by_default(tmp_path):
    html_path = tmp_path / "bank_reconciliation_probe.html"
    html_path.write_text(_build_probe_html(), encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.route(
            "**/*",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"items": []}',
            )
            if route.request.resource_type == "fetch"
            else route.continue_(),
        )
        page.goto(html_path.as_uri())
        page.evaluate(
            """
            state.workspace = {
              bank_account: { id: 10, name: 'Conta Teste' },
              selected_batch: { id: 20, batch_code: 'B1', source_type: 'ofx' },
              available_batches: [{ id: 20, batch_code: 'B1', source_type: 'ofx' }],
              bank_rows: [
                { id: 1, row_number: 1, description: 'Linha pendente', amount: 60, movement_nature: 'credit', matches: { linked_entry_ids: [], confirmed_count: 0, suggested_count: 0 }, needs_manual_action: true },
                { id: 2, row_number: 2, description: 'Linha conciliada', amount: 40, movement_nature: 'credit', created_entry_id: 999, matches: { linked_entry_ids: [999], confirmed_count: 1, suggested_count: 0 }, needs_manual_action: false }
              ],
              bank_rows_without_link: [
                { id: 1, row_number: 1, description: 'Linha pendente', amount: 60, movement_nature: 'credit', matches: { linked_entry_ids: [], confirmed_count: 0, suggested_count: 0 }, needs_manual_action: true }
              ],
              bank_rows_with_suggestion: [],
              system_rows: [],
              open_title_rows: [],
              summary: { total_rows: 2, unmatched_bank_rows: 1, confirmed_matches: 1, suggested_matches: 0 },
            };
            renderBankRows();
            """
        )

        rendered = page.locator("#bank-rows-list article").count()
        browser.close()

    assert rendered == 2
