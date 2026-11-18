from build_meta import version

def test_metadata_build_positive():
    assert version() > 0
