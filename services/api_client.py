from __future__ import annotations

import logging
import mimetypes
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from models import ApiConfig
from services.exceptions import ApiError
from utils.logging_config import sanitize

logger = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


@dataclass(slots=True)
class ApiResponse:
    status_code: int
    headers: dict[str, str]
    content_type: str
    body: bytes
    json_data: Any = None


class ApiClient:
    def __init__(self, config: ApiConfig, session: requests.Session | None = None) -> None:
        self.config = config
        self.session = session or requests.Session()

    def post_json(
        self,
        endpoint: str,
        payload: dict[str, Any],
        progress: Callable[[str], None] | None = None,
    ) -> ApiResponse:
        url = self.config.endpoint_url(endpoint)
        headers = {
            **self._auth_headers(),
            "Accept": "application/json, image/*, application/octet-stream",
            "Content-Type": "application/json",
        }
        if progress:
            progress("Đang gửi yêu cầu...")
        logger.info("POST %s payload=%s", url, sanitize(payload))
        for attempt in range(self.config.max_retries + 1):
            started = time.perf_counter()
            try:
                response = self.session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=(15, self.config.timeout_seconds),
                )
            except requests.RequestException as exc:
                logger.exception("Request failed after %.2fs", time.perf_counter() - started)
                raise ApiError(f"Không thể kết nối API: {exc}") from exc
            if not self._retry_response(response, attempt, progress):
                return self._parse_response(response, started, progress)
        raise AssertionError("Retry loop ended unexpectedly")

    def post_multipart(
        self,
        endpoint: str,
        fields: dict[str, Any],
        file_field: str,
        file_path: Path,
        progress: Callable[[str], None] | None = None,
    ) -> ApiResponse:
        url = self.config.endpoint_url(endpoint)
        headers = {
            **self._auth_headers(),
            "Accept": "application/json, image/*, application/octet-stream",
        }
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if progress:
            progress("Đang tải ảnh nguồn lên...")
        logged_fields = {**fields, file_field: f"<file:{file_path.name}:{file_path.stat().st_size} bytes>"}
        logger.info("POST multipart %s fields=%s", url, sanitize(logged_fields))
        for attempt in range(self.config.max_retries + 1):
            started = time.perf_counter()
            try:
                with file_path.open("rb") as stream:
                    response = self.session.post(
                        url,
                        headers=headers,
                        data=fields,
                        files={file_field: (file_path.name, stream, mime_type)},
                        timeout=(15, self.config.timeout_seconds),
                    )
            except OSError as exc:
                raise ApiError(f"Không thể đọc ảnh nguồn: {exc}") from exc
            except requests.RequestException as exc:
                logger.exception("Multipart request failed after %.2fs", time.perf_counter() - started)
                raise ApiError(f"Không thể kết nối API: {exc}") from exc
            if not self._retry_response(response, attempt, progress):
                return self._parse_response(response, started, progress)
        raise AssertionError("Retry loop ended unexpectedly")

    def _retry_response(
        self,
        response: requests.Response,
        attempt: int,
        progress: Callable[[str], None] | None,
    ) -> bool:
        if not self._is_retryable(response) or attempt >= self.config.max_retries:
            return False
        delay = self._retry_delay(response, attempt)
        logger.warning(
            "Retryable API status=%s; retry=%s/%s delay=%.2fs",
            response.status_code,
            attempt + 1,
            self.config.max_retries,
            delay,
        )
        if progress:
            progress(
                f"Máy chủ đang bận, thử lại lần {attempt + 1}/{self.config.max_retries} "
                f"sau {delay:g} giây..."
            )
        time.sleep(delay)
        return True

    @staticmethod
    def _is_retryable(response: requests.Response) -> bool:
        if response.status_code not in RETRYABLE_STATUS_CODES:
            return False
        if response.status_code != 429:
            return True
        message = response.text.lower()
        permanent_markers = (
            "insufficient_quota",
            "quota exceeded",
            "billing",
            "payment required",
            "余额不足",
        )
        return not any(marker in message for marker in permanent_markers)

    def _retry_delay(self, response: requests.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After", "").strip()
        try:
            if retry_after:
                return min(max(0.0, float(retry_after)), 60.0)
        except ValueError:
            pass
        return min(self.config.retry_backoff_seconds * (2**attempt), 60.0)

    def _parse_response(
        self,
        response: requests.Response,
        started: float,
        progress: Callable[[str], None] | None,
    ) -> ApiResponse:
        elapsed = time.perf_counter() - started
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        response_headers = {key: value for key, value in response.headers.items()}
        json_data: Any = None
        if "json" in content_type or response.content.lstrip().startswith((b"{", b"[")):
            try:
                json_data = response.json()
            except ValueError:
                json_data = None

        logger.info(
            "Response status=%s type=%s bytes=%s elapsed=%.2fs headers=%s body=%s",
            response.status_code,
            content_type or "unknown",
            len(response.content),
            elapsed,
            sanitize(response_headers),
            sanitize(json_data) if json_data is not None else "<binary>",
        )
        if progress:
            progress("Đang nhận dữ liệu...")
        if not response.ok:
            message = self._extract_error(json_data, response.text)
            if response.status_code == 429:
                message = self._format_rate_limit_error(message)
            raise ApiError(
                f"API trả về lỗi {response.status_code}: {message}",
                status_code=response.status_code,
            )
        return ApiResponse(
            status_code=response.status_code,
            headers=response_headers,
            content_type=content_type,
            body=response.content,
            json_data=json_data,
        )

    def _auth_headers(self) -> dict[str, str]:
        if not self.config.api_key.strip():
            raise ApiError("API Key chưa được cấu hình.")
        prefix = self.config.auth_prefix.strip()
        return {
            self.config.auth_header: f"{prefix} {self.config.api_key}".strip(),
        }

    @staticmethod
    def _extract_error(data: Any, fallback: str) -> str:
        if isinstance(data, dict):
            error = data.get("error", data)
            if isinstance(error, dict):
                for key in ("message", "detail", "error", "description"):
                    if error.get(key):
                        return str(error[key])
            if isinstance(error, str):
                return error
        cleaned = fallback.strip()
        return cleaned[:500] if cleaned else "Phản hồi không có nội dung lỗi."

    @staticmethod
    def _format_rate_limit_error(message: str) -> str:
        overload_markers = ("上游负载已饱和", "upstream", "overload", "saturated")
        if any(marker in message.lower() for marker in overload_markers):
            request_id = re.search(r"request id\s*:\s*([^)]+)", message, re.IGNORECASE)
            suffix = f" Request ID: {request_id.group(1).strip()}." if request_id else ""
            return (
                "Máy chủ của nhà cung cấp đang quá tải. Ứng dụng đã tự thử lại nhưng "
                f"vẫn chưa xử lý được; vui lòng chờ một lúc rồi thử lại.{suffix}"
            )
        return message

    def download(self, url: str) -> ApiResponse:
        headers = {"Accept": "image/*, application/octet-stream"}
        source_host = urlparse(self.config.base_url).netloc.lower()
        target_host = urlparse(url).netloc.lower()
        if source_host and target_host == source_host:
            prefix = self.config.auth_prefix.strip()
            headers[self.config.auth_header] = f"{prefix} {self.config.api_key}".strip()
        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=(15, self.config.timeout_seconds),
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ApiError(f"Không thể tải ảnh từ URL: {exc}") from exc
        return ApiResponse(
            status_code=response.status_code,
            headers={key: value for key, value in response.headers.items()},
            content_type=response.headers.get("Content-Type", "").split(";")[0].lower(),
            body=response.content,
        )
