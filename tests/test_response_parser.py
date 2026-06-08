from __future__ import annotations

import base64
import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from models import ApiConfig
from services.api_client import ApiClient, ApiResponse
from services.response_parser import ResponseParser


def png_bytes() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (8, 8), "#2463eb").save(stream, format="PNG")
    return stream.getvalue()


class FakeClient(ApiClient):
    def __init__(self, downloaded: bytes | None = None) -> None:
        super().__init__(ApiConfig(api_key="test"))
        self.downloaded = downloaded or png_bytes()

    def download(self, url: str) -> ApiResponse:
        return ApiResponse(200, {}, "image/png", self.downloaded)


class ResponseParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.parser = ResponseParser(FakeClient(), Path(self.temp.name))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_extracts_openai_response_text(self) -> None:
        response = ApiResponse(
            200,
            {},
            "application/json",
            b"{}",
            {"output": [{"content": [{"type": "output_text", "text": "Detailed prompt"}]}]},
        )
        self.assertEqual(self.parser.extract_text(response), "Detailed prompt")

    def test_extracts_chat_completion_content(self) -> None:
        response = ApiResponse(
            200,
            {},
            "application/json",
            b"{}",
            {"choices": [{"message": {"role": "assistant", "content": "Chat prompt"}}]},
        )
        self.assertEqual(self.parser.extract_text(response), "Chat prompt")

    def test_extracts_nested_base64_list(self) -> None:
        encoded = base64.b64encode(png_bytes()).decode()
        response = ApiResponse(
            200,
            {},
            "application/json",
            b"{}",
            {
                "created": 123,
                "quality": "high",
                "usage": {"total_tokens": 10},
                "result": {"images": [{"b64_json": encoded}, {"data": encoded}]},
            },
        )
        images = self.parser.extract_images(response)
        self.assertEqual(len(images), 2)
        self.assertTrue(all(image.path.exists() for image in images))
        self.assertEqual(images[0].metadata["quality"], "high")
        self.assertEqual(images[0].metadata["usage"]["total_tokens"], 10)

    def test_extracts_url(self) -> None:
        response = ApiResponse(
            200,
            {},
            "application/json",
            b"{}",
            {"url": "https://example.test/image.png"},
        )
        images = self.parser.extract_images(response)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].source, "root.url")

    def test_extracts_binary_with_generic_content_type(self) -> None:
        response = ApiResponse(200, {}, "application/octet-stream", png_bytes())
        images = self.parser.extract_images(response)
        self.assertEqual(len(images), 1)
        self.assertTrue(images[0].path.exists())

    def test_extracts_plain_text_base64(self) -> None:
        encoded = base64.b64encode(png_bytes())
        response = ApiResponse(200, {}, "text/plain", encoded)
        images = self.parser.extract_images(response)
        self.assertEqual(len(images), 1)



if __name__ == "__main__":
    unittest.main()
