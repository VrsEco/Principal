import io
import os
import sys

from flask import Flask, request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.error_handling import register_global_error_handlers


def test_api_upload_above_global_limit_returns_descriptive_413():
    app = Flask(__name__)
    app.config['TESTING'] = False
    app.config['MAX_CONTENT_LENGTH'] = 64
    register_global_error_handlers(app)

    @app.post('/api/upload-test')
    def upload_test():
        request.files.get('video')
        return {'ok': True}

    response = app.test_client().post(
        '/api/upload-test',
        data={'video': (io.BytesIO(b'x' * 128), 'video.mp4')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 413
    assert '100 MB' in response.get_json()['message']
