import re


def normalize_email(email):
    """Lowercase/trim so the same person's differently-cased email across two
    resume uploads still matches (raw extraction in parser.py preserves
    whatever casing appeared in the resume text).
    """
    if not email:
        return None
    normalized = email.strip().lower()
    return normalized or None


def normalize_phone(phone):
    """Digits-only, last 10 kept, so formatting differences (spaces, dashes,
    a leading country code) between two extractions of the same number still
    match. Not a substitute for a real phone-number library - good enough to
    catch the common cases without pulling in a new dependency for this.
    """
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    return digits[-10:] if len(digits) > 10 else digits
