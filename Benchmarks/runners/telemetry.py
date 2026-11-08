"""Normalize provider telemetry without summing nested/cumulative reports."""
import json

FIELDS = ("input_tokens", "uncached_input_tokens", "cached_input_tokens", "cache_creation_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens", "provider_total_tokens", "cost_usd", "turns", "provider_duration_ms", "model")

def blank():
    return dict.fromkeys(FIELDS)

def sum_complete(events, field):
    values = [token_value(event.get(field)) for event in events]
    return sum(values) if values and all(x is not None for x in values) else None

def token_value(value):
    if value is not None and (type(value) is not int or value < 0):
        raise ValueError("Token counts must be nonnegative integers or unavailable")
    return value

def usage_object(value):
    if not isinstance(value, dict): raise ValueError("Expected a usage object")
    return value

def codex(text):
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    # turn.completed usage is per turn; event_msg token_count and nested item usage
    # may be cumulative and must never be added a second time.
    if any(not isinstance(row, dict) for row in rows): raise ValueError("Expected JSONL event objects")
    completed = [row for row in rows if row.get("type") == "turn.completed"]
    usage = [usage_object(row.get("usage", {})) for row in completed]
    out = blank()
    for field in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"):
        out[field] = sum_complete(usage, field)
    out["provider_total_tokens"] = sum_complete(usage, "total_tokens")
    i, c, o = out["input_tokens"], out["cached_input_tokens"], out["output_tokens"]
    out["uncached_input_tokens"] = i - c if i is not None and c is not None else None
    if i is not None and c is not None and c > i:
        raise ValueError("Cached input exceeds total input")
    out["total_tokens"] = i + o if i is not None and o is not None else None
    out["turns"] = len(completed) if completed else None
    return out

def claude(text):
    data = json.loads(text)
    # Result's root usage already aggregates modelUsage and assistant turns.
    if not isinstance(data, dict) or data.get("type") != "result":
        raise ValueError("Expected a Claude Code result object")
    u = usage_object(data.get("usage", {}))
    out = blank()
    out["uncached_input_tokens"] = token_value(u.get("input_tokens"))
    out["cached_input_tokens"] = token_value(u.get("cache_read_input_tokens"))
    out["cache_creation_input_tokens"] = token_value(u.get("cache_creation_input_tokens"))
    pieces = [out[k] for k in ("uncached_input_tokens", "cached_input_tokens", "cache_creation_input_tokens")]
    out["input_tokens"] = sum(pieces) if all(x is not None for x in pieces) else None
    out["output_tokens"] = token_value(u.get("output_tokens"))
    if out["input_tokens"] is not None and out["output_tokens"] is not None:
        out["total_tokens"] = out["input_tokens"] + out["output_tokens"]
    out["reasoning_output_tokens"] = token_value(u.get("reasoning_output_tokens"))
    out["provider_total_tokens"] = token_value(u.get("total_tokens"))
    out["cost_usd"] = data.get("total_cost_usd")
    out["provider_duration_ms"] = data.get("duration_ms")
    out["turns"] = data.get("num_turns")
    out["model"] = list(data.get("modelUsage", {})) or None
    return out
