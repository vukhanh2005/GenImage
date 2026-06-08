from __future__ import annotations

import logging
from collections.abc import Callable

from services.api_client import ApiClient
from services.response_parser import ResponseParser

logger = logging.getLogger(__name__)

PROMPT_INSTRUCTIONS = """You are an expert prompt writer for AI image generation.
Expand the user's short description into one production-ready image prompt.
Preserve the user's intent and language-specific cultural details.
Add subject, environment, composition, camera/view, lighting, color, materials,
style, mood, and quality constraints where useful. Avoid unsupported claims.
Return only the final prompt, with no heading, explanation, markdown, or quotes."""


class PromptService:
    def __init__(
        self,
        client: ApiClient,
        parser: ResponseParser,
        model: str = "gpt-5.1",
    ) -> None:
        self.client = client
        self.parser = parser
        self.model = model

    def generate(self, description: str, progress: Callable[[str], None] | None = None) -> str:
        endpoint = self.client.config.prompt_endpoint
        if "chat/completions" in endpoint.lower():
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": PROMPT_INSTRUCTIONS},
                    {"role": "user", "content": description},
                ],
            }
        else:
            payload = {
                "model": self.model,
                "instructions": PROMPT_INSTRUCTIONS,
                "input": description,
            }
        response = self.client.post_json(endpoint, payload, progress)
        if isinstance(response.json_data, dict):
            actual_model = response.json_data.get("model")
            if actual_model and actual_model != self.model:
                logger.warning(
                    "Provider remapped prompt model: requested=%s actual=%s",
                    self.model,
                    actual_model,
                )
        if progress:
            progress("Đang phân tích prompt trả về...")
        return self.parser.extract_text(response)
