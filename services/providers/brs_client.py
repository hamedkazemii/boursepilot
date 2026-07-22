"""
کلاینت HTTP سطح پایین BrsApi.ir

- کلید فقط از config/env
- User-Agent مرورگر (الزام فایروال)
- بدون hardcode داده بازار
"""

from __future__ import annotations

import logging
import time
from typing import Any, Mapping, Optional
from urllib.parse import urljoin

import requests

from config import settings
from services.providers.exceptions import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderHTTPError,
)

logger = logging.getLogger(__name__)


class BrsClient:
    """GET JSON از endpointهای Tsetmc روی BrsApi."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else settings.BRS_API_KEY).strip()
        self.base_url = (base_url or settings.BRS_BASE_URL).rstrip("/") + "/"
        self.timeout = float(timeout if timeout is not None else settings.BRS_TIMEOUT_SECONDS)
        self.max_retries = int(max_retries if max_retries is not None else settings.BRS_MAX_RETRIES)

        if not self.api_key:
            raise ProviderConfigError(
                "BRS_API_KEY تنظیم نشده است. کلید را در محیط/secret قرار دهید."
            )

        self.session = session or requests.Session()
        ua = user_agent or settings.BRS_USER_AGENT
        self.session.headers.update(
            {
                "User-Agent": ua,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )

    def _url(self, endpoint: str) -> str:
        endpoint = endpoint.lstrip("/")
        return urljoin(self.base_url, endpoint)

    def get_json(
        self,
        endpoint: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """
        درخواست GET و پارس JSON.

        همیشه key به query اضافه می‌شود.
        """
        query: dict[str, Any] = {"key": self.api_key}
        if params:
            for k, v in params.items():
                if v is None:
                    continue
                query[k] = v

        url = self._url(endpoint)
        last_error: Exception | None = None

        attempts = max(1, self.max_retries + 1)
        for attempt in range(1, attempts + 1):
            try:
                logger.debug("BRS GET %s attempt=%s params=%s", endpoint, attempt, list(query))
                response = self.session.get(url, params=query, timeout=self.timeout)
                return self._parse_response(response, endpoint=endpoint)
            except ProviderAuthError:
                raise
            except (ProviderHTTPError, requests.RequestException) as exc:
                last_error = exc
                logger.warning(
                    "BRS request failed endpoint=%s attempt=%s/%s error=%s",
                    endpoint,
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    time.sleep(min(1.5 * attempt, 4.0))
                    continue
                break

        if isinstance(last_error, ProviderHTTPError):
            raise last_error
        raise ProviderHTTPError(f"BRS request failed for {endpoint}: {last_error}")

    def _parse_response(self, response: requests.Response, endpoint: str) -> Any:
        status = response.status_code
        text_head = (response.text or "")[:300]

        # تلاش برای JSON حتی روی status غیر 200
        payload: Any
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderHTTPError(
                f"پاسخ JSON نامعتبر از BRS ({endpoint}) status={status}: {text_head}",
                status_code=status,
            ) from exc

        # الگوی خطای استاندارد BrsApi
        if isinstance(payload, dict) and payload.get("successful") is False:
            message = str(payload.get("message_error") or payload.get("status") or "BRS error")
            code = payload.get("code_http") or status
            if status in (401, 403) or code in (401, 403) or payload.get("status") == "unauthorized":
                raise ProviderAuthError(message, status_code=int(code) if code else status, payload=payload)
            raise ProviderHTTPError(message, status_code=int(code) if code else status, payload=payload)

        if status == 401 or status == 403:
            raise ProviderAuthError(
                f"دسترسی BRS رد شد status={status}",
                status_code=status,
                payload=payload,
            )

        if status >= 400:
            raise ProviderHTTPError(
                f"خطای HTTP BRS status={status} endpoint={endpoint}: {text_head}",
                status_code=status,
                payload=payload,
            )

        return payload
