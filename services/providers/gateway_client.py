"""کلاینت سطح پایین برای اتصال به Market Gateway داخلی.

- هیچ URL/IP هاردکد نیست — فقط از Environment Variables
- اگر MARKET_GATEWAY_URL تنظیم نشده باشد، خطای شفاف می‌دهد
- پشتیبانی از token اختیاری برای احراز هویت
"""

from __future__ import annotations

import os

import logging
from typing import Any, Mapping, Optional
from urllib.parse import urljoin

import requests

from config import settings
from services.providers.exceptions import ProviderConfigError, ProviderHTTPError

logger = logging.getLogger(__name__)


class MarketGatewayClient:
    """کلاینت HTTP برای Market Gateway داخلی."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: Optional[float] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        env_url = os.getenv("MARKET_GATEWAY_URL")

        if env_url == "":
            raise ProviderConfigError(
                "MARKET_GATEWAY_URL empty"
            )

        self.base_url = (
            base_url
            or env_url
            or settings.MARKET_GATEWAY_URL
            or ""
        ).rstrip("/") + "/"
        self.token = (token or settings.MARKET_GATEWAY_TOKEN or "").strip()
        self.timeout = float(timeout if timeout is not None else settings.GATEWAY_TIMEOUT_SECONDS)

        if not self.base_url or self.base_url == "/":
            raise ProviderConfigError(
                "MARKET_GATEWAY_URL تنظیم نشده است. "
                "سیستم به‌صورت خودکار وارد Demo Mode می‌شود."
            )

        self.session = session or requests.Session()
        self.session.headers.update({
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "fa-IR,fa;q=0.9",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def _url(self, endpoint: str) -> str:
        endpoint = endpoint.lstrip("/")
        return urljoin(self.base_url, endpoint)

    def get_json(
        self,
        endpoint: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """درخواست GET و بازگرداندن JSON."""
        url = self._url(endpoint)
        logger.info("Gateway GET %s", endpoint)
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ProviderHTTPError(
                f"اتصال به Gateway ناموفق ({endpoint}): {exc}",
            ) from exc

        return self._parse_response(response, endpoint=endpoint)

    def _parse_response(self, response: requests.Response, endpoint: str) -> Any:
        status = response.status_code
        text_head = (response.text or "")[:300]

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderHTTPError(
                f"پاسخ JSON نامعتبر از Gateway ({endpoint}) status={status}: {text_head}",
                status_code=status,
            ) from exc

        if status == 200:
            return payload

        if status == 401:
            raise ProviderHTTPError(
                "دسترسی Gateway رد شد (401). Token معتبر نیست.",
                status_code=401,
            )
        if status == 404:
            raise ProviderHTTPError(
                f"endpoint Gateway یافت نشد: {endpoint}",
                status_code=404,
            )

        # خطای عمومی
        message = ""
        if isinstance(payload, dict):
            message = str(payload.get("message") or payload.get("error") or "")
        raise ProviderHTTPError(
            f"خطای Gateway status={status} endpoint={endpoint}: {message or text_head}",
            status_code=status,
        )
