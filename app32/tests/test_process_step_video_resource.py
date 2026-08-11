import io
import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.resources import process as process_resource


class _FakeStepQuery:
    def __init__(self, step):
        self.step = step

    def get_or_404(self, step_id):
        return self.step


def _build_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test'
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    return app


def test_process_step_put_accepts_video_upload(monkeypatch):
    app = _build_app()
    saved_paths = []
    committed = {'value': False}
    step = SimpleNamespace(
        id=19,
        name='Passo',
        description='',
        expected_result='',
        layout='single',
        image_path=None,
        video_path=None,
        video_duration_seconds=None,
        image_width=280,
        order_index=1,
    )

    monkeypatch.setattr(process_resource, 'ProcessStep', SimpleNamespace(query=_FakeStepQuery(step)))
    monkeypatch.setattr(process_resource, '_get_process_step_with_access', lambda step_id, action='view': step)
    monkeypatch.setattr(process_resource, 'save_pop_video', lambda file, subfolder='': saved_paths.append((file.filename, subfolder)) or f'{subfolder}/passo-comprimido.mp4')
    monkeypatch.setattr(process_resource, 'delete_file', lambda path: True)
    monkeypatch.setattr(process_resource.db.session, 'commit', lambda: committed.__setitem__('value', True))
    monkeypatch.setattr(process_resource, 'process_step_schema', SimpleNamespace(dump=lambda current: {
        'id': current.id,
        'video_path': current.video_path,
        'video_duration_seconds': current.video_duration_seconds,
        'layout': current.layout,
    }))

    data = {
        'layout': 'single',
        'video_duration_seconds': '48',
        'video': (io.BytesIO(b'video-bytes'), 'passo.mp4'),
    }

    with app.test_request_context('/api/process-steps/19', method='PUT', data=data, content_type='multipart/form-data'):
        response, status = process_resource.ProcessStepResource().put.__wrapped__(process_resource.ProcessStepResource(), 19)

    assert status == 200
    assert response['video_path'] == 'pop/video/passo-comprimido.mp4'
    assert response['video_duration_seconds'] == 48
    assert saved_paths == [('passo.mp4', 'pop/video')]
    assert committed['value'] is True


def test_process_step_put_rejects_video_above_limit(monkeypatch):
    app = _build_app()
    rolled_back = {'value': False}
    step = SimpleNamespace(
        id=20,
        name='Passo',
        description='',
        expected_result='',
        layout='single',
        image_path=None,
        video_path=None,
        video_duration_seconds=None,
        image_width=280,
        order_index=1,
    )

    monkeypatch.setattr(process_resource, 'ProcessStep', SimpleNamespace(query=_FakeStepQuery(step)))
    monkeypatch.setattr(process_resource, '_get_process_step_with_access', lambda step_id, action='view': step)
    monkeypatch.setattr(process_resource, 'save_file', lambda file, subfolder='': f'{subfolder}/{file.filename}')
    monkeypatch.setattr(process_resource.db.session, 'rollback', lambda: rolled_back.__setitem__('value', True))

    data = {
        'video_duration_seconds': '151',
        'video': (io.BytesIO(b'video-bytes'), 'passo.mp4'),
    }

    with app.test_request_context('/api/process-steps/20', method='PUT', data=data, content_type='multipart/form-data'):
        response, status = process_resource.ProcessStepResource().put.__wrapped__(process_resource.ProcessStepResource(), 20)

    assert status == 400
    assert '2 minutos e 30 segundos' in response['error']
    assert rolled_back['value'] is True


def test_process_step_delete_uses_process_step_resource(monkeypatch):
    app = _build_app()
    deleted_paths = []
    deleted_step = {'value': None}
    committed = {'value': False}
    step = SimpleNamespace(
        id=21,
        image_path='pop/imagem.png',
        video_path='pop/video/passo.mp4',
    )

    monkeypatch.setattr(process_resource, 'ProcessStep', SimpleNamespace(query=_FakeStepQuery(step)))
    monkeypatch.setattr(process_resource, '_get_process_step_with_access', lambda step_id, action='view': step)
    monkeypatch.setattr(process_resource, 'delete_file', lambda path: deleted_paths.append(path) or True)
    monkeypatch.setattr(process_resource.db.session, 'delete', lambda current: deleted_step.__setitem__('value', current))
    monkeypatch.setattr(process_resource.db.session, 'commit', lambda: committed.__setitem__('value', True))

    with app.test_request_context('/api/process-steps/21', method='DELETE'):
        response, status = process_resource.ProcessStepResource().delete.__wrapped__(process_resource.ProcessStepResource(), 21)

    assert status == 200
    assert response['message'] == 'Step deleted successfully'
    assert deleted_paths == ['pop/imagem.png', 'pop/video/passo.mp4']
    assert deleted_step['value'] is step
    assert committed['value'] is True


def test_process_step_get_denies_cross_tenant_access(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(
        process_resource,
        '_get_process_step_with_access',
        lambda step_id, action='view': None,
    )

    with app.test_request_context('/api/process-steps/99', method='GET'):
        response, status = process_resource.ProcessStepResource().get.__wrapped__(
            process_resource.ProcessStepResource(),
            99,
        )

    assert status == 403
    assert 'Permission denied' in response['error']
