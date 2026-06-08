from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from models import ApiConfig
from services.api_client import ApiClient
from services.exceptions import ApiError


class ApiClientTests(unittest.TestCase):
    def test_reads_status_headers_and_json(self) -> None:
        response = Mock()
        response.status_code = 200
        response.ok = True
        response.headers = {"Content-Type": "application/json; charset=utf-8", "X-Request-Id": "r1"}
        response.content = b'{"url":"https://example.test/a.png"}'
        response.text = response.content.decode()
        response.json.return_value = {"url": "https://example.test/a.png"}
        session = Mock()
        session.post.return_value = response
        client = ApiClient(ApiConfig(api_key="secret"), session)

        result = client.post_json("/images/generations", {"model": "test"})

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.content_type, "application/json")
        self.assertEqual(result.headers["X-Request-Id"], "r1")
        self.assertEqual(result.json_data["url"], "https://example.test/a.png")
        sent_headers = session.post.call_args.kwargs["headers"]
        self.assertEqual(sent_headers["Authorization"], "Bearer secret")

    def test_raises_api_error_with_server_message(self) -> None:
        response = Mock()
        response.status_code = 429
        response.ok = False
        response.headers = {"Content-Type": "application/json"}
        response.content = b'{"error":{"message":"rate limited"}}'
        response.text = response.content.decode()
        response.json.return_value = {"error": {"message": "rate limited"}}
        session = Mock()
        session.post.return_value = response
        client = ApiClient(ApiConfig(api_key="secret"), session)

        with self.assertRaisesRegex(ApiError, "rate limited"):
            client.post_json("/responses", {"model": "test"})

    def test_download_only_sends_auth_to_same_host(self) -> None:
        response = Mock()
        response.status_code = 200
        response.headers = {"Content-Type": "image/png"}
        response.content = b"image"
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        client = ApiClient(
            ApiConfig(api_key="secret", base_url="https://api.example.test/v1"),
            session,
        )

        client.download("https://api.example.test/files/image.png")
        same_host_headers = session.get.call_args.kwargs["headers"]
        self.assertEqual(same_host_headers["Authorization"], "Bearer secret")

        client.download("https://cdn.example.test/image.png")
        other_host_headers = session.get.call_args.kwargs["headers"]
        self.assertNotIn("Authorization", other_host_headers)

    def test_posts_multipart_image_without_forcing_content_type(self) -> None:
        response = Mock()
        response.status_code = 200
        response.ok = True
        response.headers = {"Content-Type": "application/json"}
        response.content = b'{"data":[]}'
        response.text = response.content.decode()
        response.json.return_value = {"data": []}
        session = Mock()
        session.post.return_value = response
        client = ApiClient(ApiConfig(api_key="secret"), session)

        with tempfile.TemporaryDirectory() as folder:
            image_path = Path(folder) / "source.png"
            image_path.write_bytes(b"png-data")
            result = client.post_multipart(
                "/images/edits",
                {"model": "gpt-image-1.5", "prompt": "edit"},
                "image",
                image_path,
            )

        kwargs = session.post.call_args.kwargs
        self.assertNotIn("Content-Type", kwargs["headers"])
        self.assertEqual(kwargs["data"]["prompt"], "edit")
        self.assertEqual(kwargs["files"]["image"][0], "source.png")
        self.assertEqual(result.status_code, 200)


if __name__ == "__main__":
    unittest.main()
