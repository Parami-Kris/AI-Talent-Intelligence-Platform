from pipeline.parser import extract_email, extract_links, extract_phone


def test_extract_email_finds_first_address():
    text = "Contact me at jane.doe@example.com or backup@example.org"
    assert extract_email(text) == "jane.doe@example.com"


def test_extract_email_returns_none_when_absent():
    assert extract_email("No contact info here.") is None


def test_extract_phone_finds_number():
    text = "Call me at +1 415-555-0132 for details."
    assert extract_phone(text) is not None


def test_extract_phone_returns_none_when_absent():
    assert extract_phone("No phone number here.") is None


def test_extract_links_splits_linkedin_and_github():
    text = (
        "Portfolio: https://linkedin.com/in/janedoe "
        "and https://github.com/janedoe "
        "and https://example.com/blog"
    )
    links = extract_links(text)

    assert links["linkedin"] == ["https://linkedin.com/in/janedoe"]
    assert links["github"] == ["https://github.com/janedoe"]
    assert len(links["all"]) == 3


def test_extract_links_returns_none_for_missing_categories():
    links = extract_links("No links here.")
    assert links["linkedin"] is None
    assert links["github"] is None
    assert links["all"] == []