from pathlib import Path


def test_indicator_tree_nodes_are_resolved_inside_the_active_company():
    source = (Path(__file__).resolve().parents[1] / 'api' / 'routes' / 'indicators.py').read_text(encoding='utf-8')
    assert source.count('IndicatorTree.query.filter_by(id=node_id, company_id=company_id).first_or_404()') == 2
    assert 'IndicatorTree.query.get_or_404(node_id)' not in source
