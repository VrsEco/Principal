"""Narrow Z-API adapter: no chat/contact access and no secret-bearing errors."""
from dataclasses import dataclass
import logging
import re
import requests


class _TokenPathRedaction(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(r'(/token/)[^/\s?]+', r'\1[REDACTED]', record.getMessage())
        record.args = ()
        return True


# urllib3 DEBUG/WARNING messages can contain the path even when the application
# never logs exceptions. Redact at the emitting logger, before all handlers.
_transport_logger = logging.getLogger('urllib3.connectionpool')
if not any(isinstance(f, _TokenPathRedaction) for f in _transport_logger.filters):
    _transport_logger.addFilter(_TokenPathRedaction())


@dataclass(frozen=True)
class StatusResult:
    status: str
    code: str
    message_id: str | None = None


class ZApiStatusProvider:
    def __init__(self, config, post=None, get=None):
        # Never stringify this config, URL, exceptions or provider response bodies.
        self._config = config
        self._post = post or requests.post
        self._get = get or requests.get

    def _url(self, method):
        instance = self._config.get('instance_id')
        token = self._config.get('api_key')
        client = self._config.get('client_token')
        if not all(isinstance(v, str) and v.strip() for v in (instance, token, client)):
            raise ValueError('status_credentials_missing')
        if not all(re.fullmatch(r'[A-Za-z0-9_-]+', v) for v in (instance, token)):
            raise ValueError('status_credentials_invalid')
        return f'https://api.z-api.io/instances/{instance}/token/{token}/{method}'

    def _headers(self):
        return {'Client-Token': self._config['client_token'], 'Content-Type': 'application/json'}

    def send_image(self, image_base64):
        try:
            url = self._url('send-image-status')
        except ValueError:
            return StatusResult('failed', 'configuration_missing')
        try:
            response = self._post(url, json={'image': image_base64}, headers=self._headers(),
                                  timeout=(5, 30), allow_redirects=False)
            if response.status_code == 200:
                data = response.json()
                mid = data.get('messageId') if isinstance(data, dict) else None
                if (isinstance(mid, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,120}', mid)
                    and mid not in (self._config.get('api_key'), self._config.get('client_token'))):
                    return StatusResult('accepted', 'provider_accepted', mid)
                return StatusResult('unknown', 'invalid_acceptance_response')
            # 5xx/redirect/408 may follow a successful upstream side effect.
            if 400 <= response.status_code < 500 and response.status_code not in (408,):
                return StatusResult('failed', f'http_{response.status_code}')
            return StatusResult('unknown', 'provider_result_uncertain')
        except Exception:
            # requests errors frequently embed token-bearing URLs. Never persist str(exc).
            return StatusResult('unknown', 'transport_or_response_uncertain')

    def connected_phone(self):
        """Read-only device inspection, never reconnect or modify a webhook."""
        try:
            status_response = self._get(self._url('status'), headers=self._headers(),
                                        timeout=(5, 15), allow_redirects=False)
            state = status_response.json() if status_response.status_code == 200 else None
            if not isinstance(state, dict) or state.get('connected') is not True:
                raise ValueError('status_instance_not_connected')
            response = self._get(self._url('device'), headers=self._headers(),
                                 timeout=(5, 15), allow_redirects=False)
            if response.status_code != 200:
                raise ValueError('status_device_unavailable')
            data = response.json()
            phone = data.get('phone') if isinstance(data, dict) else None
            phone = re.sub(r'\D', '', phone) if isinstance(phone, str) else ''
            if not re.fullmatch(r'\d{10,15}', phone):
                raise ValueError('status_device_phone_unavailable')
            return phone
        except Exception:
            raise ValueError('status_device_unavailable') from None
