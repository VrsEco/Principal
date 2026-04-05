from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (BASE_DIR / relative_path).read_text(encoding='utf-8')


def test_process_instances_template_supports_origin_shortcut_focus():
    content = _read('templates/modules/processes/process_instances_list.html')

    assert 'instance_id' in content
    assert 'focusPendingInstanceCard' in content
    assert 'data-instance-id="${inst.id}"' in content
    assert 'is-focused-origin' in content
