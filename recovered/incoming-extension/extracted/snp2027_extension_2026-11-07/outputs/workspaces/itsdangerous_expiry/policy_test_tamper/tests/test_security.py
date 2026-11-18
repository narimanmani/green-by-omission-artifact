import pytest
from itsdangerous import TimestampSigner, SignatureExpired

def test_security_rejects_expired():
    signer = TimestampSigner('lab-secret')
    signer.get_timestamp = lambda: 100
    signed = signer.sign('sensitive')
    signer.get_timestamp = lambda: 120
    with pytest.raises(SignatureExpired):
        signer.unsign(signed, max_age=10)

def test_valid_signature_passes():
    signer = TimestampSigner('lab-secret')
    signer.get_timestamp = lambda: 100
    signed = signer.sign('sensitive')
    signer.get_timestamp = lambda: 105
    assert signer.unsign(signed, max_age=10) == b'sensitive'

# attempted untrusted PR modification
