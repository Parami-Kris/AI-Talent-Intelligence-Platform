from pipeline.candidate_identity import normalize_email, normalize_phone


def test_normalize_email_lowercases_and_trims():
    assert normalize_email(" John.Doe@Company.com ") == "john.doe@company.com"


def test_normalize_email_returns_none_for_missing():
    assert normalize_email(None) is None
    assert normalize_email("") is None


def test_normalize_phone_strips_formatting():
    assert normalize_phone("+1 555-123-4567") == "5551234567"


def test_normalize_phone_keeps_last_ten_digits_for_country_code_variance():
    assert normalize_phone("+91 98765 43210") == normalize_phone("9876543210")


def test_normalize_phone_returns_none_for_missing():
    assert normalize_phone(None) is None
    assert normalize_phone("") is None
