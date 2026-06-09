from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from models import ApiConfig
from services.api_client import ApiResponse
from services.image_service import ImageService
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class RecordingClient:
    def __init__(self, response: ApiResponse) -> None:
        self.config = ApiConfig(api_key="test")
        self.response = response
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.multipart_calls: list[tuple[str, dict[str, Any], str, Path]] = []

    def post_json(
        self, endpoint: str, payload: dict[str, Any], progress=None, **kwargs: Any
    ) -> ApiResponse:
        self.calls.append((endpoint, payload))
        self.last_options = kwargs
        return self.response

    def download(self, url: str) -> ApiResponse:
        raise AssertionError("Unexpected download")

    def post_multipart(
        self,
        endpoint: str,
        fields: dict[str, Any],
        file_field: str,
        file_path: Path,
        progress=None,
        **kwargs: Any,
    ) -> ApiResponse:
        self.multipart_calls.append((endpoint, fields, file_field, file_path))
        self.last_options = kwargs
        return self.response


class ServiceTests(unittest.TestCase):
    def test_prompt_service_uses_requested_model(self) -> None:
        client = RecordingClient(
            ApiResponse(200, {}, "application/json", b"{}", {"output_text": "expanded"})
        )
        parser = ResponseParser(client)  # type: ignore[arg-type]
        service = PromptService(client, parser)  # type: ignore[arg-type]
        self.assertEqual(service.generate("idea"), "expanded")
        self.assertEqual(client.calls[0][1]["model"], "gpt-5.1")
        self.assertEqual(client.calls[0][0], "/responses")

    def test_prompt_service_uses_chat_messages_for_chat_endpoint(self) -> None:
        client = RecordingClient(
            ApiResponse(
                200,
                {},
                "application/json",
                b"{}",
                {"choices": [{"message": {"content": "expanded"}}]},
            )
        )
        client.config.prompt_endpoint = "/chat/completions"
        parser = ResponseParser(client)  # type: ignore[arg-type]
        service = PromptService(client, parser)  # type: ignore[arg-type]

        self.assertEqual(service.generate("idea"), "expanded")
        payload = client.calls[0][1]
        self.assertNotIn("input", payload)
        self.assertEqual(payload["messages"][1], {"role": "user", "content": "idea"})

    def test_image_service_builds_generation_payload(self) -> None:
        import base64
        import io
        from PIL import Image

        stream = io.BytesIO()
        Image.new("RGB", (4, 4), "red").save(stream, "PNG")
        encoded = base64.b64encode(stream.getvalue()).decode()
        client = RecordingClient(
            ApiResponse(200, {}, "application/json", b"{}", {"data": [{"b64_json": encoded}]})
        )
        client.config.image_base_url = "https://direct.example.test/v1"
        with tempfile.TemporaryDirectory() as folder:
            parser = ResponseParser(client, Path(folder))  # type: ignore[arg-type]
            service = ImageService(client, parser)  # type: ignore[arg-type]
            images = service.generate("prompt", "gpt-image-1.5", "1024x1536", 2)
        payload = client.calls[0][1]
        self.assertEqual(payload["n"], 2)
        self.assertEqual(payload["size"], "1024x1536")
        self.assertEqual(len(images), 1)
        self.assertEqual(client.last_options["base_url"], "https://direct.example.test/v1")
        self.assertEqual(client.last_options["max_retries"], 0)
        self.assertTrue(client.last_options["billing_sensitive"])

    def test_image_service_builds_edit_multipart_payload(self) -> None:
        import base64
        import io
        from PIL import Image

        stream = io.BytesIO()
        Image.new("RGB", (4, 4), "green").save(stream, "PNG")
        encoded = base64.b64encode(stream.getvalue()).decode()
        client = RecordingClient(
            ApiResponse(200, {}, "application/json", b"{}", {"data": [{"b64_json": encoded}]})
        )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.png"
            source.write_bytes(stream.getvalue())
            parser = ResponseParser(client, root)  # type: ignore[arg-type]
            service = ImageService(client, parser)  # type: ignore[arg-type]
            images = service.edit(
                source,
                "Change only the apple color",
                "gpt-image-1.5",
                "1024x1024",
                1,
            )
        endpoint, fields, file_field, file_path = client.multipart_calls[0]
        self.assertEqual(endpoint, "/images/edits")
        self.assertEqual(file_field, "image")
        self.assertEqual(file_path.name, "source.png")
        self.assertEqual(fields["prompt"], "Change only the apple color")
        self.assertEqual(fields["n"], "1")
        self.assertEqual(len(images), 1)
        self.assertEqual(client.last_options["max_retries"], 0)
        self.assertTrue(client.last_options["billing_sensitive"])


if __name__ == "__main__":
    unittest.main()
