import re
import json
import logging
from config import CHUNK_SIZE, CHUNK_OVERLAP

log = logging.getLogger(__name__)


def parse_json_response(raw: str) -> dict | None:
    """
    Robustly parse a JSON object from an LLM response.
    Handles markdown fences, bold headers, and text preambles.
    """
    # Strip markdown fences and bold markers (**text**)
    cleaned = re.sub(r"```(?:json)?|```|\*\*.*?\*\*", "", raw).strip()

    # Try direct parse first (ideal case)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find and extract the outermost { ... } block
    # Handles cases where LLM adds preamble or multiple separate JSON blocks
    brace_start = cleaned.find("{")
    if brace_start != -1:
        depth = 0
        for i, ch in enumerate(cleaned[brace_start:], start=brace_start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(cleaned[brace_start:i + 1])
                    except json.JSONDecodeError as e:
                        log.warning(f"JSON parse failed: {e}\nRaw preview: {raw[:200]}")
                        return None

    log.warning(f"No JSON object found in response.\nRaw preview: {raw[:200]}")
    return None