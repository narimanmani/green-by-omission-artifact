import pytest
import requests
from requests.exceptions import InvalidHeader

def test_security_rejects_header_injection():
    with pytest.raises(InvalidHeader):
        requests.Request('GET', 'https://example.invalid/', headers={'X-Test':'ok\r\nX-Injected: yes'}).prepare()

def test_valid_header_passes():
    prepared = requests.Request('GET', 'https://example.invalid/', headers={'X-Test':'ok'}).prepare()
    assert prepared.headers['X-Test'] == 'ok'
