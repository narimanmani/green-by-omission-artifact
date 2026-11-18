from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.testclient import TestClient

async def handler(request):
    return PlainTextResponse('hello')

def make_app():
    return Starlette(routes=[Route('/', handler)], middleware=[Middleware(TrustedHostMiddleware, allowed_hosts=['good.example'], www_redirect=False)])

def test_security_rejects_untrusted_host():
    client = TestClient(make_app())
    response = client.get('http://evil.example/')
    assert response.status_code == 400

def test_valid_host_passes():
    client = TestClient(make_app())
    response = client.get('http://good.example/')
    assert response.status_code == 200
