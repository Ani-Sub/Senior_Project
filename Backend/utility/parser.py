import re
import json
import logging

log = logging.getLogger(__name__)


def repair_unquoted_strings(s: str) -> str:
    """
    Repair JSON with unquoted string values.
    Handles cases like: "text": AI will replace jobs,
    Converts to: "text": "AI will replace jobs",
    """
    lines = s.split('\n')
    repaired_lines = []
    
    for line in lines:
        # Pattern: "key": value where value is unquoted
        # Match: "key": <something that's not quoted, a number, bool, null, { or [>
        match = re.match(r'^(\s*"[^"]+"\s*:\s*)([^"\[\{\d\s][^,\}\]]*?)\s*([,\}\]]?\s*)$', line)
        
        if match:
            prefix = match.group(1)  # "key": 
            value = match.group(2).strip()
            suffix = match.group(3)  # , or } or ]
            
            # Skip if it's a valid JSON value
            if value in ('true', 'false', 'null'):
                repaired_lines.append(line)
                continue
            
            # Skip if it looks like a number
            try:
                float(value)
                repaired_lines.append(line)
                continue
            except ValueError:
                pass
            
            # It's an unquoted string - quote it
            value = value.replace('\\', '\\\\').replace('"', '\\"')
            repaired_lines.append(f'{prefix}"{value}"{suffix}')
        else:
            repaired_lines.append(line)
    
    return '\n'.join(repaired_lines)


def repair_truncated_json(s: str) -> str:
    """
    Attempt to repair truncated JSON by closing open brackets/braces.
    This handles cases where LLM response gets cut off mid-JSON.
    """
    # First try to repair unquoted strings
    s = repair_unquoted_strings(s)
    
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
    Handles markdown fences, bold headers, text preambles, unquoted strings, and truncated JSON.
    """
    # Strip markdown fences and bold markers (**text**)
    cleaned = re.sub(r"```(?:json)?|```|\*\*.*?\*\*", "", raw).strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try repairing unquoted strings
    repaired = repair_unquoted_strings(cleaned)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    brace_start = cleaned.find("{")
    if brace_start == -1:
        log.warning(f"No JSON object found in response.\nRaw preview: {raw[:300]}")
        return None

    truncated = cleaned[brace_start:]
    depth = 0
    last_complete_pos = -1

    for i, ch in enumerate(truncated):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                last_complete_pos = i
                break

    if last_complete_pos != -1:
        block = truncated[:last_complete_pos + 1]
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            repaired_block = repair_unquoted_strings(block)
            try:
                return json.loads(repaired_block)
            except json.JSONDecodeError as e:
                log.warning(f"JSON parse failed: {e}\nRaw preview: {raw[:300]}")
                # Fall through to truncation repair

    # JSON was truncated — try to repair it
    log.warning("Attempting to repair truncated JSON...")
    repaired = repair_truncated_json(truncated)
    try:
        result = json.loads(repaired)
        log.info("  → JSON repair successful")
        return result
    except json.JSONDecodeError:
        pass

    # Last resort: salvage just the claims array
    match = re.search(r'"claims"\s*:\s*(\[.*)', truncated, re.DOTALL)
    if match:
        try:
            partial = match.group(1)
            partial_repaired = repair_truncated_json('{"claims":' + partial + "}")
            result = json.loads(partial_repaired)
            log.warning("  → Salvaged partial claims array from truncated JSON")
            return result
        except json.JSONDecodeError:
            pass

    log.warning(f"JSON repair failed.\nRaw preview: {raw[:300]}")
    return None