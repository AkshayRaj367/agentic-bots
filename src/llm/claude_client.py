from anthropic import Anthropic

from src.config import Config


class Claude:
    def __init__(self):
        config = Config()
        api_key = config.get_claude_api_key()
        self.client = Anthropic(
            api_key=api_key,
        )

    @staticmethod
    def _normalize_model_id(model_id: str) -> str:
        deprecated_map = {
            "claude-3-opus-20240229": "claude-3-7-sonnet-20250219",
            "claude-3-sonnet-20240229": "claude-3-7-sonnet-20250219",
            "claude-3-haiku-20240307": "claude-3-5-haiku-20241022",
            "claude-3-5-sonnet-latest": "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-latest": "claude-3-5-haiku-20241022",
            "claude-3-7-sonnet-latest": "claude-3-7-sonnet-20250219",
        }
        return deprecated_map.get(model_id, model_id)

    @staticmethod
    def _fallback_models(primary_model_id: str):
        # Try account-safe dated models if one specific alias/id is unavailable.
        fallbacks = {
            "claude-3-7-sonnet-20250219": [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-sonnet-20240620",
            ],
            "claude-3-5-sonnet-20241022": [
                "claude-3-7-sonnet-20250219",
                "claude-3-5-sonnet-20240620",
            ],
            "claude-3-5-sonnet-20240620": [
                "claude-3-5-sonnet-20241022",
                "claude-3-7-sonnet-20250219",
            ],
            "claude-3-5-haiku-20241022": [
                "claude-3-haiku-20240307",
                "claude-3-5-sonnet-20241022",
            ],
            "claude-3-haiku-20240307": [
                "claude-3-5-haiku-20241022",
                "claude-3-5-sonnet-20241022",
            ],
        }
        return [primary_model_id] + fallbacks.get(primary_model_id, [])

    def _available_model_ids(self):
        try:
            models_resp = self.client.models.list()
            data = getattr(models_resp, "data", None)
            if data is None and isinstance(models_resp, dict):
                data = models_resp.get("data", [])
            if data is None:
                return set()

            ids = set()
            for item in data:
                item_id = getattr(item, "id", None)
                if item_id is None and isinstance(item, dict):
                    item_id = item.get("id")
                if item_id:
                    ids.add(item_id)
            return ids
        except Exception:
            return set()

    @staticmethod
    def _pick_preferred_available_model(available_ids):
        # Prefer Sonnet for balanced cost/quality when auto-selecting from account models.
        ordered = sorted(available_ids)
        for keyword in ("sonnet", "haiku", "opus"):
            for model_id in ordered:
                if keyword in model_id:
                    return model_id
        return ordered[0] if ordered else None

    def inference(self, model_id: str, prompt: str) -> str:
        model_id = self._normalize_model_id(model_id)
        last_error = None
        available_ids = self._available_model_ids()
        candidate_models = self._fallback_models(model_id)

        if available_ids:
            filtered = [m for m in candidate_models if m in available_ids]
            if filtered:
                candidate_models = filtered
            else:
                # Last resort: pick a preferred available Claude model on the account.
                preferred = self._pick_preferred_available_model(available_ids)
                if preferred:
                    candidate_models = [preferred]

        for candidate_model in candidate_models:
            try:
                message = self.client.messages.create(
                    max_tokens=4096,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt.strip(),
                        }
                    ],
                    model=candidate_model,
                    temperature=0
                )
                return message.content[0].text
            except Exception as e:
                last_error = e
                # Continue trying other compatible IDs only for model-not-found scenarios.
                if "not_found_error" not in str(e) and "model:" not in str(e):
                    raise

        raise last_error
