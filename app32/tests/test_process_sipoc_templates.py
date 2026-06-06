import os


def test_process_details_template_places_sipoc_before_flow():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'templates',
            'modules',
            'processes',
            'process_details_v2.html',
        )
    )
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    sipoc_idx = content.index("switchTab('sipoc')")
    flow_idx = content.index("switchTab('modeling')")

    assert sipoc_idx < flow_idx
    assert 'SIPOC do Processo' in content
    assert 'Enquadre o processo em nível macro antes do fluxo BPMN' in content
    assert 'Process · Atividades do processo' in content


def test_process_map_template_places_macro_sipoc_after_macros():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'templates',
            'modules',
            'processes',
            'process_map_v2.html',
        )
    )
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    macros_idx = content.index("switchTab('macros')")
    macro_sipoc_idx = content.index("switchTab('macro-sipoc')")
    processes_idx = content.index("switchTab('processes')")

    assert macros_idx < macro_sipoc_idx < processes_idx
    assert 'SIPOC de Macroprocesso' in content


def test_process_book_template_renders_sipoc_before_flow_section():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'templates',
            'reports',
            'process_book_v2.html',
        )
    )
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    sipoc_idx = content.index('{% if sipoc %}')
    flow_idx = content.index('<section class="page section-flow">')

    assert sipoc_idx < flow_idx
    assert 'Requisitos regulatórios aplicáveis' in content
