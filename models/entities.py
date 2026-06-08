from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ApiConfig:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    prompt_endpoint: str = "/responses"
    image_endpoint: str = "/images/generations"
    image_edit_endpoint: str = "/images/edits"
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer"
    timeout_seconds: int = 180

    def endpoint_url(self, endpoint: str) -> str:
        return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"


@dataclass(slots=True)
class ImageArtifact:
    path: Path
    mime_type: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class HistoryEntry:
    time: str
    input_prompt: str
    generated_prompt: str
    image_path: str
    model: str
    size: str
    image_paths: list[str] = field(default_factory=list)
    mode: str = "generate"
    source_image_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "HistoryEntry":
        primary = str(value.get("image_path", ""))
        paths = value.get("image_paths")
        if not isinstance(paths, list):
            paths = [primary] if primary else []
        return cls(
            time=str(value.get("time", "")),
            input_prompt=str(value.get("input_prompt", "")),
            generated_prompt=str(value.get("generated_prompt", "")),
            image_path=primary,
            model=str(value.get("model", "")),
            size=str(value.get("size", "")),
            image_paths=[str(path) for path in paths],
            mode=str(value.get("mode", "generate")),
            source_image_path=str(value.get("source_image_path", "")),
        )
