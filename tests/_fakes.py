class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeGenAIClient:
    """Stands in for google.genai.Client so tests never hit the real Gemini API.

    Pass response_text for a single fixed reply, or responses for a list
    consumed in order across successive generate_content calls.
    """

    def __init__(self, response_text=None, responses=None):
        self._response_text = response_text
        self._responses = list(responses) if responses is not None else None

    def _next_text(self):
        if self._responses is not None:
            return self._responses.pop(0)
        return self._response_text

    @property
    def models(self):
        return self

    def generate_content(self, model, contents):
        return FakeResponse(self._next_text())
