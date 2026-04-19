# create wrapper function that will has retry logic of 5 times
import sys
import time
from functools import wraps
import json
import re

from src.socket_instance import emit_agent

def retry_wrapper(func):
    def wrapper(*args, **kwargs):
        max_tries = 5
        tries = 0
        while tries < max_tries:
            result = func(*args, **kwargs)
            if result:
                return result
            print("Invalid response from the model, I'm trying again...")
            emit_agent("info", {"type": "warning", "message": "Invalid response from the model, trying again..."})
            tries += 1
            time.sleep(2)
        print("Maximum 5 attempts reached. try other models")
        emit_agent("info", {"type": "error", "message": "Maximum attempts reached. model keeps failing."})
        return False
    return wrapper

        
class InvalidResponseError(Exception):
    pass


def _extract_json_candidates(text: str):
    candidates = [text]

    # Common model wrappers: ```json ... ``` and ~~~ ... ~~~
    fenced_blocks = re.findall(r"(?:```|~~~)(?:json)?\s*([\s\S]*?)(?:```|~~~)", text, flags=re.IGNORECASE)
    candidates.extend(fenced_blocks)

    decoder = json.JSONDecoder()
    for candidate in list(candidates):
        s = candidate.strip()
        for i, ch in enumerate(s):
            if ch not in "[{":
                continue
            try:
                parsed, end = decoder.raw_decode(s[i:])
                if parsed is not None:
                    yield parsed
                tail = s[i + end :].strip()
                if tail:
                    for line in tail.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue
            except json.JSONDecodeError:
                continue

def validate_responses(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        args = list(args)
        response = args[1]
        if isinstance(response, (dict, list)):
            args[1] = response
            return func(*args, **kwargs)

        response = str(response).strip()
        for parsed in _extract_json_candidates(response):
            args[1] = parsed
            result = func(*args, **kwargs)
            if result is not False:
                return result

        # If all else fails, raise an exception
        emit_agent("info", {"type": "error", "message": "Failed to parse response as JSON"})
        # raise InvalidResponseError("Failed to parse response as JSON")
        return False

    return wrapper