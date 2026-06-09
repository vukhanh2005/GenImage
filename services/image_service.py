from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from models import ImageArtifact
from services.api_client import ApiClient
from services.response_parser import ResponseParser


class ImageService:
    def __init__(self, client: ApiClient, parser: ResponseParser) -> None:
        self.client = client
        self.parser = parser

    def generate(
        self,
        prompt: str,
        model: str,
        size: str,
        count: int,
        progress: Callable[[str], None] | None = None,
    ) -> list[ImageArtifact]:
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": count,
            "output_format": "png",
        }
        response = self.client.post_json(
            self.client.config.image_endpoint,
            payload,
            progress,
            base_url=self.client.config.image_base_url or None,
            max_retries=0,
            billing_sensitive=True,
        )
        if progress:
            progress("Đang xử lý ảnh...")
        return self.parser.extract_images(response)

    def edit(
        self,
        source_image: Path,
        prompt: str,
        model: str,
        size: str,
        count: int,
        progress: Callable[[str], None] | None = None,
    ) -> list[ImageArtifact]:
        fields = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": str(count),
            "output_format": "png",
        }
        response = self.client.post_multipart(
            self.client.config.image_edit_endpoint,
            fields,
            "image",
            source_image,
            progress,
            base_url=self.client.config.image_base_url or None,
            max_retries=0,
            billing_sensitive=True,
        )
        if progress:
            progress("Đang xử lý ảnh đã chỉnh sửa...")
        return self.parser.extract_images(response)
