import re
import json
import logging

log = logging.getLogger(__name__)


def repair_truncated_json(s: str) -> str:
    """
    Attempt to repair truncated JSON by closing open brackets/braces.
    This handles cases where LLM response gets cut off mid-JSON.
    """
    # Count open brackets
    open_braces = s.count('{') - s.count('}')
    open_brackets = s.count('[') - s.count(']')
    
    # Check if we're inside an unclosed string
    in_string = False
    escaped = False
    for ch in s:
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
    
    # If in unclosed string, close it
    if in_string:
        s = s + '"'
    
    # Remove trailing comma if present (common truncation artifact)
    s = re.sub(r',\s*$', '', s)
    
    # Close open brackets and braces
    s = s + (']' * open_brackets) + ('}' * open_braces)
    
    return s


def parse_json_response(raw: str) -> dict | None:
    """
    Robustly parse a JSON object from an LLM response.
    Handles markdown fences, bold headers, text preambles, and truncated JSON.
    """
    # Strip markdown fences and bold markers (**text**)
    cleaned = re.sub(r"```(?:json)?|```|\*\*.*?\*\*", "", raw).strip()

    # Try direct parse first (ideal case)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find and extract the outermost { ... } block
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
        
        # If we get here, JSON was truncated (unclosed braces)
        # Try to repair it
        truncated = cleaned[brace_start:]
        log.warning(f"Attempting to repair truncated JSON...")
        repaired = repair_truncated_json(truncated)
        try:
            result = json.loads(repaired)
            log.info(f"  → JSON repair successful")
            return result
        except json.JSONDecodeError as e:
            log.warning(f"JSON repair failed: {e}\nRaw preview: {raw[:200]}")
            return None

    log.warning(f"No JSON object found in response.\nRaw preview: {raw[:200]}")
    return None