import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_llm_json(raw_text: str) -> Any:
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Error parsing JSON from model response", exc_info=True)
        return {"error": str(e), "raw_response": cleaned}
