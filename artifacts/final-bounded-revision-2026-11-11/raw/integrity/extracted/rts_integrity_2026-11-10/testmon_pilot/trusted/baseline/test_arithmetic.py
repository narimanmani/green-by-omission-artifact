from arithmetic import add

def test_positive():
    assert add(2, 2) == 4

def test_negative():
    assert add(-2, -2) == -4
