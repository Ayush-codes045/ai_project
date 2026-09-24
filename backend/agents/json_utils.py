import json
import re


def extract_json(content: str) -> dict:
    """Robustly extract a JSON object from an LLM response.

    Handles three cases:
      1. Pure JSON (returned when response_format=json_object is used).
      2. JSON wrapped in a ```json ... ``` or ``` ... ``` markdown fence.
      3. JSON embedded in surrounding prose (falls back to first {...} block).

    Raises json.JSONDecodeError if no valid JSON can be parsed.
    """
    if content is None:
        raise json.JSONDecodeError("Empty content", "", 0)

    text = content.strip()

    # Fast path: already valid JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences if present
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Last resort: grab the outermost {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise json.JSONDecodeError("No JSON object found", text, 0)