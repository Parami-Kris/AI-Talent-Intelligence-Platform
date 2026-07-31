from backend.app.services import llm_provider


def test_chat_completion_json_returns_mistral_result_without_calling_groq(monkeypatch):
    calls = []
    monkeypatch.setattr(llm_provider, "_call_mistral", lambda *a, **k: calls.append("mistral") or {"ok": True})
    monkeypatch.setattr(llm_provider, "_call_groq", lambda *a, **k: calls.append("groq") or {"ok": False})

    result = llm_provider.chat_completion_json("prompt")

    assert calls == ["mistral"]
    assert result == {"ok": True}


def test_chat_completion_json_falls_back_to_groq_when_mistral_fails(monkeypatch):
    calls = []
    monkeypatch.setattr(llm_provider, "_call_mistral", lambda *a, **k: calls.append("mistral") or None)
    monkeypatch.setattr(llm_provider, "_call_groq", lambda *a, **k: calls.append("groq") or {"ok": True})

    result = llm_provider.chat_completion_json("prompt")

    assert calls == ["mistral", "groq"]
    assert result == {"ok": True}


def test_chat_completion_json_returns_none_when_both_providers_fail(monkeypatch):
    monkeypatch.setattr(llm_provider, "_call_mistral", lambda *a, **k: None)
    monkeypatch.setattr(llm_provider, "_call_groq", lambda *a, **k: None)

    assert llm_provider.chat_completion_json("prompt") is None


def test_call_mistral_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    assert llm_provider._call_mistral("prompt", 100) is None


def test_call_groq_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    assert llm_provider._call_groq("prompt", 100) is None
