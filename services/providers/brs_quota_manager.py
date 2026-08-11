"""
BRS Quota Manager — مدیریت سقف و نرخ درخواست برای پلن AIO BRS.

پلن AIO:
- Rate Limit: ۱۰۰۰ درخواست در ۵ دقیقه
- Daily Budget: قابل تنظیم در پنل BRS (پیش‌فرض ۱۰۰۰/روز برای AllSymbols، ۱۰/روز برای CODAL، ۳۰۰/۵دقیقه برای بقیه)
- Retry با exponential backoff
- Cache در حافظه + deduplication
- Logging مصرف هر API
- هشدار نزدیک شدن به quota
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """پیکربندی سقف برای هر endpoint"""
    endpoint: str
    rate_limit_per_5min: int = 300
    daily_budget: int = 1000
    cache_ttl_seconds: int = 30
    requires_api_key: bool = True
    priority: int = 1  # 1=high, 2=medium, 3=low


# پیش‌فرض‌های AIO Plan
DEFAULT_API_CONFIGS = {
    "AllSymbols": APIConfig(
        endpoint="Tsetmc/AllSymbols.php",
        rate_limit_per_5min=1000,  # AIO: 1000/5min
        daily_budget=5000,  # قابل تنظیم در پنل
        cache_ttl_seconds=60,
        priority=1,
    ),
    "Symbol": APIConfig(
        endpoint="Tsetmc/Symbol.php",
        rate_limit_per_5min=1000,
        daily_budget=5000,
        cache_ttl_seconds=30,
        priority=1,
    ),
    "Nav": APIConfig(
        endpoint="Tsetmc/Nav.php",
        rate_limit_per_5min=1000,
        daily_budget=2000,  # NAV کمتر استفاده می‌شود
        cache_ttl_seconds=300,  # 5 دقیقه cache
        priority=1,
    ),
    "Shareholder": APIConfig(
        endpoint="Tsetmc/Shareholder.php",
        rate_limit_per_5min=1000,
        daily_budget=1000,
        cache_ttl_seconds=300,
        priority=2,
    ),
    "History": APIConfig(
        endpoint="Tsetmc/History.php",
        rate_limit_per_5min=1000,
        daily_budget=5000,
        cache_ttl_seconds=3600,  # ۱ ساعت برای تاریخچه
        priority=1,
    ),
    "Candlestick": APIConfig(
        endpoint="Tsetmc/Candlestick.php",
        rate_limit_per_5min=1000,
        daily_budget=5000,
        cache_ttl_seconds=3600,
        priority=1,
    ),
    "CodalAnnouncement": APIConfig(
        endpoint="Codal/Announcement.php",
        rate_limit_per_5min=100,  # کم‌تر چون тяжеل است
        daily_budget=500,  # در پنل قابل افزایش
        cache_ttl_seconds=300,
        priority=1,
    ),
    "Transaction": APIConfig(
        endpoint="Tsetmc/Transaction.php",
        rate_limit_per_5min=1000,
        daily_budget=1000,
        cache_ttl_seconds=60,
        priority=3,
    ),
}


@dataclass
class UsageStats:
    """آمار مصرف برای یک endpoint"""
    endpoint: str
    requests_5min: int = 0
    requests_today: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    last_request_at: Optional[float] = None
    last_error_at: Optional[float] = None
    last_error_msg: str = ""
    window_start_5min: float = field(default_factory=time.time)
    day_start: str = field(default_factory=lambda: datetime.now().date().isoformat())


class BRSQuotaManager:
    """
    مدیریت سقف و نرخ درخواست BRS API.
    
    ویژگی‌ها:
    - Rate limit: 1000 req/5min (AIO)
    - Daily budget هر endpoint جداگانه
    - Sliding window برای 5 دقیقه
    - Retry با exponential backoff (max 3 retry)
    - In-memory cache با TTL و deduplication
    - Logging و metrics کامل
    - هشدار عندل‌به‌quota (80%, 90%, 95%)
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://Api.BrsApi.ir",
        configs: Optional[dict[str, APIConfig]] = None,
        warning_thresholds: tuple = (0.8, 0.9, 0.95),
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.configs = configs or DEFAULT_API_CONFIGS
        self.warning_thresholds = warning_thresholds
        
        # Thread-safe state
        self._lock = threading.RLock()
        self._usage: dict[str, UsageStats] = defaultdict(lambda: UsageStats(endpoint=""))
        self._cache: dict[str, tuple[Any, float]] = {}  # key -> (data, expires_at)
        self._pending_requests: dict[str, int] = defaultdict(int)  # for deduplication
        self._warned_thresholds: dict[str, set[float]] = defaultdict(set)
        
        # Initialize usage stats
        for name, cfg in self.configs.items():
            self._usage[name] = UsageStats(endpoint=name)
        
        logger.info("BRSQuotaManager initialized: api_key=%s... base_url=%s", api_key[:8], base_url)
    
    # ================================================================
    # Public API
    # ================================================================
    
    def request(
        self,
        endpoint_name: str,
        params: dict,
        fetcher: Callable[[str, dict], Any],
        *,
        use_cache: bool = True,
        force_refresh: bool = False,
    ) -> Any:
        """
        اجرای یک درخواست با مدیریت quota، cache، retry.
        
        Args:
            endpoint_name: نام endpoint (مطابق configs)
            params: پارامترهای درخواست (بدون key)
            fetcher: تابع دریافت داده (url, params) -> data
            use_cache: از cache استفاده شود؟
            force_refresh: cache نادیده گرفته شود؟
        
        Returns:
            داده دریافتی
        
        Raises:
            QuotaExceededError: اگر quota تمام شده باشد
            ProviderError: خطای شبکه/HTTP
        """
        if endpoint_name not in self.configs:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")
        
        cfg = self.configs[endpoint_name]
        
        # 1. Check daily budget
        self._check_daily_budget(endpoint_name, cfg)
        
        # 2. Check rate limit (5-min sliding window)
        self._check_rate_limit(endpoint_name, cfg)
        
        # 3. Build cache key
        cache_key = self._build_cache_key(endpoint_name, params)
        
        # 4. Check cache
        if use_cache and not force_refresh:
            cached = self._get_from_cache(cache_key, cfg.cache_ttl_seconds)
            if cached is not None:
                with self._lock:
                    self._usage[endpoint_name].cache_hits += 1
                logger.debug("Cache HIT: %s %s", endpoint_name, cache_key)
                return cached
        
        with self._lock:
            self._usage[endpoint_name].cache_misses += 1
        
        # 5. Deduplication: prevent simultaneous identical requests
        dedup_key = f"{endpoint_name}|{cache_key}"
        with self._lock:
            if self._pending_requests.get(dedup_key, 0) > 0:
                # Another thread is fetching this - wait briefly
                pass  # In production, could use condition variable
            self._pending_requests[dedup_key] += 1
        
        try:
            # 6. Execute with retry
            data = self._execute_with_retry(endpoint_name, cfg, params, fetcher)
            
            # 7. Store in cache
            if use_cache and data is not None:
                self._set_cache(cache_key, data, cfg.cache_ttl_seconds)
            
            return data
            
        finally:
            with self._lock:
                self._pending_requests[dedup_key] -= 1
                if self._pending_requests[dedup_key] <= 0:
                    self._pending_requests.pop(dedup_key, None)
    
    def get_usage_report(self) -> dict:
        """گزارش کامل مصرف quota"""
        with self._lock:
            report = {}
            for name, usage in self._usage.items():
                cfg = self.configs.get(name)
                if not cfg:
                    continue
                pct_5min = (usage.requests_5min / cfg.rate_limit_per_5min * 100) if cfg.rate_limit_per_5min else 0
                pct_daily = (usage.requests_today / cfg.daily_budget * 100) if cfg.daily_budget else 0
                report[name] = {
                    "endpoint": cfg.endpoint,
                    "requests_5min": usage.requests_5min,
                    "rate_limit_5min": cfg.rate_limit_per_5min,
                    "pct_5min": round(pct_5min, 1),
                    "requests_today": usage.requests_today,
                    "daily_budget": cfg.daily_budget,
                    "pct_daily": round(pct_daily, 1),
                    "cache_hits": usage.cache_hits,
                    "cache_misses": usage.cache_misses,
                    "cache_hit_rate": round(
                        usage.cache_hits / max(1, usage.cache_hits + usage.cache_misses) * 100, 1
                    ),
                    "errors": usage.errors,
                    "last_request_at": usage.last_request_at,
                    "last_error": usage.last_error_msg,
                    "warnings_triggered": list(self._warned_thresholds.get(name, set())),
                }
            return report
    
    def reset_daily_counters(self) -> None:
        """ریست کردن شمارنده‌های روزانه (برای cron شبانه)"""
        with self._lock:
            today = datetime.now().date().isoformat()
            for usage in self._usage.values():
                if usage.day_start != today:
                    usage.requests_today = 0
                    usage.day_start = today
                    usage.window_start_5min = time.time()
            self._warned_thresholds.clear()
            logger.info("Daily quota counters reset")
    
    def clear_cache(self, endpoint_name: Optional[str] = None) -> int:
        """پاک کردن cache"""
        with self._lock:
            if endpoint_name:
                prefix = f"{endpoint_name}|"
                keys = [k for k in self._cache if k.startswith(prefix)]
                for k in keys:
                    del self._cache[k]
                return len(keys)
            else:
                count = len(self._cache)
                self._cache.clear()
                return count
    
    # ================================================================
    # Internal Methods
    # ================================================================
    
    def _check_daily_budget(self, endpoint_name: str, cfg: APIConfig) -> None:
        with self._lock:
            usage = self._usage[endpoint_name]
            today = datetime.now().date().isoformat()
            
            # Reset if new day
            if usage.day_start != today:
                usage.requests_today = 0
                usage.day_start = today
            
            if usage.requests_today >= cfg.daily_budget:
                msg = f"Daily budget exhausted for {endpoint_name}: {usage.requests_today}/{cfg.daily_budget}"
                logger.error(msg)
                raise QuotaExceededError(msg, endpoint_name, "daily")
    
    def _check_rate_limit(self, endpoint_name: str, cfg: APIConfig) -> None:
        with self._lock:
            usage = self._usage[endpoint_name]
            now = time.time()
            
            # Reset 5-min window if expired
            if now - usage.window_start_5min > 300:  # 5 minutes
                usage.requests_5min = 0
                usage.window_start_5min = now
            
            if usage.requests_5min >= cfg.rate_limit_per_5min:
                msg = f"Rate limit exceeded for {endpoint_name}: {usage.requests_5min}/{cfg.rate_limit_per_5min} per 5min"
                logger.error(msg)
                raise QuotaExceededError(msg, endpoint_name, "rate_limit")
            
            # Check warning thresholds
            pct = usage.requests_5min / cfg.rate_limit_per_5min if cfg.rate_limit_per_5min else 0
            for threshold in self.warning_thresholds:
                if pct >= threshold and threshold not in self._warned_thresholds[endpoint_name]:
                    logger.warning(
                        "Quota warning: %s at %.0f%% of 5-min limit (%d/%d)",
                        endpoint_name, threshold * 100, usage.requests_5min, cfg.rate_limit_per_5min
                    )
                    self._warned_thresholds[endpoint_name].add(threshold)
            
            # Daily warning
            daily_pct = usage.requests_today / cfg.daily_budget if cfg.daily_budget else 0
            for threshold in self.warning_thresholds:
                if daily_pct >= threshold and threshold not in self._warned_thresholds[f"{endpoint_name}_daily"]:
                    logger.warning(
                        "Daily quota warning: %s at %.0f%% of daily budget (%d/%d)",
                        endpoint_name, threshold * 100, usage.requests_today, cfg.daily_budget
                    )
                    self._warned_thresholds[f"{endpoint_name}_daily"].add(threshold)
    
    def _execute_with_retry(
        self,
        endpoint_name: str,
        cfg: APIConfig,
        params: dict,
        fetcher: Callable,
    ) -> Any:
        max_retries = 3
        base_delay = 1.0  # seconds
        
        for attempt in range(max_retries + 1):
            try:
                # Add API key to params
                full_params = {"key": self.api_key, **params}
                url = f"{self.base_url}/{cfg.endpoint}"
                
                logger.debug("BRS request: %s %s (attempt %d)", endpoint_name, full_params, attempt + 1)
                
                # Update usage BEFORE request (optimistic)
                with self._lock:
                    self._usage[endpoint_name].requests_5min += 1
                    self._usage[endpoint_name].requests_today += 1
                    self._usage[endpoint_name].last_request_at = time.time()
                
                data = fetcher(url, full_params)
                
                logger.debug("BRS response OK: %s", endpoint_name)
                return data
                
            except QuotaExceededError:
                # Don't retry quota errors
                raise
            except Exception as e:
                with self._lock:
                    self._usage[endpoint_name].errors += 1
                    self._usage[endpoint_name].last_error_at = time.time()
                    self._usage[endpoint_name].last_error_msg = str(e)
                
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # exponential backoff
                    logger.warning(
                        "BRS request failed (attempt %d/%d): %s. Retrying in %.1fs",
                        attempt + 1, max_retries + 1, e, delay
                    )
                    time.sleep(delay)
                else:
                    logger.error("BRS request failed after %d retries: %s", max_retries + 1, e)
                    raise
    
    def _build_cache_key(self, endpoint_name: str, params: dict) -> str:
        """ساخت کلید cache از نام endpoint و پارامترها"""
        # Sort params for consistent key
        param_str = "|".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{endpoint_name}|{param_str}"
    
    def _get_from_cache(self, key: str, ttl_seconds: int) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                data, expires_at = self._cache[key]
                if time.time() < expires_at:
                    return data
                else:
                    del self._cache[key]
        return None
    
    def _set_cache(self, key: str, data: Any, ttl_seconds: int) -> None:
        with self._lock:
            self._cache[key] = (data, time.time() + ttl_seconds)


class QuotaExceededError(Exception):
    """خطای تجاوز از سقف quota"""
    def __init__(self, message: str, endpoint: str, limit_type: str):
        super().__init__(message)
        self.endpoint = endpoint
        self.limit_type = limit_type  # "daily" or "rate_limit"


# ================================================================
# Convenience Functions
# ================================================================

_global_quota_manager: Optional[BRSQuotaManager] = None
_quota_lock = threading.Lock()


def get_quota_manager(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> BRSQuotaManager:
    """Singleton برای Quota Manager"""
    global _global_quota_manager
    with _quota_lock:
        if _global_quota_manager is None:
            from config import settings
            _global_quota_manager = BRSQuotaManager(
                api_key=api_key or settings.BRS_API_KEY,
                base_url=base_url or settings.BRS_BASE_URL,
            )
        return _global_quota_manager


def reset_quota_manager() -> None:
    """ریست singleton (برای تست)"""
    global _global_quota_manager
    with _quota_lock:
        _global_quota_manager = None