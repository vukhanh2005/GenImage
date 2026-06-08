from __future__ import annotations

import base64
import binascii
import io
import re
import uuid
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, UnidentifiedImageError

from models import ImageArtifact
from services.api_client import ApiClient, ApiResponse
from services.exceptions import ResponseParseError
from utils.paths import TEMP_DIR

URL_RE = re.compile(r"^https?://", re.IGNORECASE)
DATA_URL_RE = re.compile(r"^data:(image/[^;]+);base64,(.+)$", re.IGNORECASE | re.DOTALL)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
IMAGE_KEYS = {
    "b64_json",
    "base64",
    "image",
    "image_base64",
    "image_data",
    "url",
    "image_url",
    "output",
    "result",
    "data",
    "images",
}


class ResponseParser:
    def __init__(self, api_client: ApiClient, temp_dir: Path = TEMP_DIR) -> None:
        self.api_client = api_client
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def extract_text(self, response: ApiResponse) -> str:
        data = response.json_data
        if isinstance(data, str) and data.strip():
            return data.strip()
        candidates: list[str] = []
        self._collect_text(data, candidates)
        for text in candidates:
            cleaned = text.strip()
            if cleaned and not self._looks_like_image_value(cleaned):
                return cleaned
        if response.body and response.content_type.startswith("text/"):
            return response.body.decode("utf-8", errors="replace").strip()
        raise ResponseParseError("Không tìm thấy nội dung prompt trong phản hồi API.")

    def extract_images(self, response: ApiResponse) -> list[ImageArtifact]:
        metadata = self._extract_metadata(response.json_data)
        if response.body and (
            response.content_type.startswith("image/")
            or response.content_type == "application/octet-stream"
            or response.json_data is None
        ):
            try:
                artifact = self._save_image_bytes(response.body, response.content_type, "binary")
                artifact.metadata = metadata
                return [artifact]
            except ResponseParseError:
                pass

        candidates: list[tuple[str, Any]] = []
        self._collect_image_candidates(response.json_data, candidates)
        if response.json_data is None and response.body:
            try:
                raw_text = response.body.decode("utf-8").strip()
            except UnicodeDecodeError:
                raw_text = ""
            if raw_text:
                candidates.append(("text_body", raw_text))
        artifacts: list[ImageArtifact] = []
        errors: list[str] = []
        for source, candidate in candidates:
            try:
                artifact = self._candidate_to_artifact(candidate, source)
                if artifact:
                    artifact.metadata = metadata
                    artifacts.append(artifact)
            except (ResponseParseError, OSError) as exc:
                errors.append(str(exc))
        if artifacts:
            return artifacts
        detail = f" Chi tiết: {'; '.join(errors[:3])}" if errors else ""
        raise ResponseParseError(f"Không tìm thấy dữ liệu ảnh hợp lệ trong phản hồi API.{detail}")

    def _candidate_to_artifact(self, value: Any, source: str) -> ImageArtifact | None:
        if isinstance(value, dict):
            for key in ("b64_json", "base64", "image_base64", "image_data", "url", "image_url", "data"):
                if key in value:
                    return self._candidate_to_artifact(value[key], f"{source}.{key}")
            return None
        if not isinstance(value, str):
            return None
        value = value.strip()
        data_url = DATA_URL_RE.match(value)
        if data_url:
            return self._save_image_bytes(
                self._decode_base64(data_url.group(2)),
                data_url.group(1).lower(),
                source,
            )
        if URL_RE.match(value):
            downloaded = self.api_client.download(value)
            return self._save_image_bytes(downloaded.body, downloaded.content_type, source)
        try:
            decoded = self._decode_base64(value)
        except ResponseParseError:
            return None
        return self._save_image_bytes(decoded, "", source)

    def _save_image_bytes(self, data: bytes, mime_type: str, source: str) -> ImageArtifact:
        if not data:
            raise ResponseParseError("Dữ liệu ảnh rỗng.")
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
                detected_format = (image.format or "PNG").lower()
        except (UnidentifiedImageError, OSError) as exc:
            raise ResponseParseError("Dữ liệu nhận được không phải ảnh hợp lệ.") from exc
        extension = ".jpg" if detected_format == "jpeg" else f".{detected_format}"
        detected_mime = Image.MIME.get(detected_format.upper(), mime_type or "application/octet-stream")
        path = self.temp_dir / f"generated_{uuid.uuid4().hex}{extension}"
        path.write_bytes(data)
        return ImageArtifact(path=path, mime_type=detected_mime, source=source)

    @staticmethod
    def _decode_base64(value: str) -> bytes:
        compact = re.sub(r"\s+", "", value)
        if len(compact) < 32:
            raise ResponseParseError("Chuỗi base64 quá ngắn.")
        compact += "=" * (-len(compact) % 4)
        try:
            return base64.b64decode(compact, validate=True)
        except (binascii.Error, ValueError) as exc:
            try:
                return base64.urlsafe_b64decode(compact)
            except (binascii.Error, ValueError) as urlsafe_exc:
                raise ResponseParseError("Base64 không hợp lệ.") from urlsafe_exc

    def _collect_image_candidates(self, value: Any, output: list[tuple[str, Any]], path: str = "root") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                child_path = f"{path}.{key}"
                if key.lower() in IMAGE_KEYS and not isinstance(item, (list, dict)):
                    output.append((child_path, item))
                else:
                    self._collect_image_candidates(item, output, child_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                self._collect_image_candidates(item, output, f"{path}[{index}]")
        elif isinstance(value, str) and self._looks_like_image_value(value):
            output.append((path, value))

    def _collect_text(self, value: Any, output: list[str]) -> None:
        if isinstance(value, dict):
            for key in ("output_text", "text", "content", "message", "result", "response"):
                item = value.get(key)
                if isinstance(item, str):
                    output.append(item)
                elif key == "content" and isinstance(item, list):
                    for content_item in item:
                        if isinstance(content_item, dict):
                            text = content_item.get("text")
                            if isinstance(text, str):
                                output.append(text)
            for item in value.values():
                self._collect_text(item, output)
        elif isinstance(value, list):
            for item in value:
                self._collect_text(item, output)

    @staticmethod
    def _looks_like_image_value(value: str) -> bool:
        stripped = value.strip()
        if DATA_URL_RE.match(stripped) or URL_RE.match(stripped):
            return True
        if len(stripped) > 100 and re.fullmatch(r"[A-Za-z0-9+/=\s_-]+", stripped):
            return True
        return Path(stripped).suffix.lower() in IMAGE_EXTENSIONS

    @staticmethod
    def _extract_metadata(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        metadata: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in IMAGE_KEYS:
                continue
            if isinstance(item, (str, int, float, bool)) or item is None:
                metadata[key] = item
            elif isinstance(item, dict):
                metadata[key] = item
        return metadata
