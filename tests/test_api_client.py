from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

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
        client = ApiClient(ApiConfig(api_key="secret", max_retries=0), session)

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
        client = ApiClient(ApiConfig(api_key="secret", max_retries=0), session)

        with self.assertRaisesRegex(ApiError, "rate limited"):
            client.post_json("/responses", {"model": "test"})

    @patch("services.api_client.time.sleep")
    def test_retries_temporary_rate_limit_and_then_succeeds(self, sleep: Mock) -> None:
        busy = Mock()
        busy.status_code = 429
        busy.ok = False
        busy.headers = {"Content-Type": "application/json", "Retry-After": "3"}
        busy.content = b'{"error":{"message":"upstream overloaded"}}'
        busy.text = busy.content.decode()
        busy.json.return_value = {"error": {"message": "upstream overloaded"}}

        success = Mock()
        success.status_code = 200
        success.ok = True
        success.headers = {"Content-Type": "application/json"}
        success.content = b'{"data":[]}'
        success.text = success.content.decode()
        success.json.return_value = {"data": []}

        session = Mock()
        session.post.side_effect = [busy, success]
        progress = Mock()
        client = ApiClient(ApiConfig(api_key="secret", max_retries=2), session)

        result = client.post_json("/images/generations", {"model": "test"}, progress)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(session.post.call_count, 2)
        sleep.assert_called_once_with(3.0)
        self.assertIn("thử lại lần 1/2", progress.call_args_list[1].args[0])

    def test_translates_upstream_saturation_error(self) -> None:
        response = Mock()
        response.status_code = 429
        response.ok = False
        response.headers = {"Content-Type": "text/plain"}
        response.content = (
            "当前分组上游负载已饱和，请稍后再试 "
            "(request id: 20260609143127829295063V1Cu6u9X)"
        ).encode()
        response.text = response.content.decode()
        session = Mock()
        session.post.return_value = response
        client = ApiClient(ApiConfig(api_key="secret", max_retries=0), session)

        with self.assertRaisesRegex(ApiError, "Máy chủ của nhà cung cấp đang quá tải") as raised:
            client.post_json("/images/generations", {"model": "test"})

        self.assertIn("20260609143127829295063V1Cu6u9X", str(raised.exception))

    @patch("services.api_client.time.sleep")
    def test_does_not_retry_insufficient_quota(self, sleep: Mock) -> None:
        response = Mock()
        response.status_code = 429
        response.ok = False
        response.headers = {"Content-Type": "application/json"}
        response.content = b'{"error":{"code":"insufficient_quota","message":"quota exceeded"}}'
        response.text = response.content.decode()
        response.json.return_value = {
            "error": {"code": "insufficient_quota", "message": "quota exceeded"}
        }
        session = Mock()
        session.post.return_value = response
        client = ApiClient(ApiConfig(api_key="secret", max_retries=2), session)

        with self.assertRaisesRegex(ApiError, "quota exceeded"):
            client.post_json("/images/generations", {"model": "test"})

        self.assertEqual(session.post.call_count, 1)
        sleep.assert_not_called()

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
