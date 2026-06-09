from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from models import ImageArtifact
from services.api_client import ApiClient, ApiResponse
from services.exceptions import ApiError
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
        def request(candidate: str) -> ApiResponse:
            payload = {
                "model": candidate,
                "prompt": prompt,
                "size": size,
                "n": count,
                "output_format": "png",
            }
            return self.client.post_json(
                self.client.config.image_endpoint,
                payload,
                progress,
                **self._request_options(),
            )

        return self._run_with_fallback(
            model,
            request,
            "Đang xử lý ảnh...",
            progress,
        )

    def edit(
        self,
        source_image: Path,
        prompt: str,
        model: str,
        size: str,
        count: int,
        progress: Callable[[str], None] | None = None,
    ) -> list[ImageArtifact]:
        def request(candidate: str) -> ApiResponse:
            fields = {
                "model": candidate,
                "prompt": prompt,
                "size": size,
                "n": str(count),
                "output_format": "png",
            }
            return self.client.post_multipart(
                self.client.config.image_edit_endpoint,
                fields,
                "image",
                source_image,
                progress,
                **self._request_options(),
            )

        return self._run_with_fallback(
            model,
            request,
            "Đang xử lý ảnh đã chỉnh sửa...",
            progress,
        )

    def _run_with_fallback(
        self,
        selected_model: str,
        request: Callable[[str], ApiResponse],
        success_status: str,
        progress: Callable[[str], None] | None,
    ) -> list[ImageArtifact]:
        candidates = self._model_candidates(selected_model)
        for index, candidate in enumerate(candidates):
            try:
                response = request(candidate)
            except ApiError as exc:
                next_model = candidates[index + 1] if index + 1 < len(candidates) else None
                if exc.reason != "model_unavailable" or not next_model:
                    raise
                if progress:
                    progress(f"Có lỗi xảy ra. Đang đổi sang model {next_model}")
                continue
            if progress:
                progress(success_status)
            return self._extract_images(response, candidate)
        raise AssertionError("Model fallback loop ended unexpectedly")

    def _model_candidates(self, selected_model: str) -> list[str]:
        return list(dict.fromkeys((selected_model, *self.client.config.image_models)))

    def _request_options(self) -> dict[str, Any]:
        return {
            "base_url": self.client.config.image_base_url or None,
            "max_retries": 0,
            "billing_sensitive": True,
        }

    def _extract_images(self, response: ApiResponse, model: str) -> list[ImageArtifact]:
        artifacts = self.parser.extract_images(response)
        for artifact in artifacts:
            artifact.metadata["model"] = model
        return artifacts
