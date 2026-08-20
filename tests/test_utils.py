from patch.manifest_utils import is_version_at_least


def test_is_version_at_least_standard():
    assert is_version_at_least("1.13.2", "1.13.1") is True
    assert is_version_at_least("1.13.1", "1.13.2") is False
    assert is_version_at_least("2.0.0", "1.9.9") is True
    assert is_version_at_least("1.13", "1.13.0") is True  # 1.13 vs 1.13.0
    assert is_version_at_least("1.13.0", "1.13") is True  # 1.13.0 vs 1.13


def test_is_version_at_least_operators():
    # >= operator
    assert is_version_at_least("1.13.2", ">=1.13.1") is True
    assert is_version_at_least("1.13.1", ">=1.13.2") is False

    # <= operator
    assert is_version_at_least("1.13.1", "<=1.13.2") is True
    assert is_version_at_least("1.13.2", "<=1.13.1") is False

    # > operator
    assert is_version_at_least("1.13.2", ">1.13.1") is True
    assert is_version_at_least("1.13.2", ">1.13.2") is False

    # < operator
    assert is_version_at_least("1.13.1", "<1.13.2") is True
    assert is_version_at_least("1.13.1", "<1.13.1") is False

    # == and = operator
    assert is_version_at_least("1.13.2", "==1.13.2") is True
    assert is_version_at_least("1.13.2", "=1.13.2") is True
    assert is_version_at_least("1.13.1", "==1.13.2") is False

    # multiple operators
    assert is_version_at_least("1.13.5", ">=1.13.0, <=1.14.0") is True
    assert is_version_at_least("1.15.0", ">=1.13.0, <=1.14.0") is False
    assert is_version_at_least("1.12.0", ">=1.13.0, <=1.14.0") is False
    assert is_version_at_least("1.13.2", ">1.13.0,<1.14.0") is True


def test_is_version_at_least_rc():
    # Final is greater than rc
    assert is_version_at_least("1.13.2", "1.13.2rc2") is True
    assert is_version_at_least("1.13.2rc2", "1.13.2") is False

    # rc is greater than previous version
    assert is_version_at_least("1.13.2rc2", "1.13.1") is True
    assert is_version_at_least("1.13.1", "1.13.2rc2") is False

    # Compare rcs
    assert is_version_at_least("1.13.2rc3", "1.13.2rc2") is True
    assert is_version_at_least("1.13.2rc2", "1.13.2rc3") is False

    # Same rc
    assert is_version_at_least("1.13.2rc2", "1.13.2rc2") is True


def test_is_version_at_least_invalid():
    assert is_version_at_least("abc", "1.13.1") is False
    assert is_version_at_least("1.13.1", "abc") is False
    assert is_version_at_least("1.13.x", "1.13.1") is False
    assert is_version_at_least(None, "1.13.1") is False
    assert is_version_at_least("1.13.1", None) is False


def test_is_version_at_least_missing_dots():
    assert is_version_at_least("2", "1") is True
    assert is_version_at_least("1", "2") is False
