"""موتور ساعات بازار ایران — تعیین جلسات معاملاتی و گزارش‌گیری."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from enum import Enum
from typing import Optional
import jdatetime  # تقویم شمسی


class SessionName(str, Enum):
    PRE_OPEN = "pre_open"       # ۰۸:۴۵-۰۹:۰۰ پیش‌سفارش
    MORNING = "morning"         # ۰۹:۰۰-۱۲:۰۰ صبح
    MIDDAY = "midday"           # ۱۱:۰۰-۱۵:۰۰ میانی (تداخل)
    AFTERNOON = "afternoon"     # ۱۵:۰۰-۱۷:۰۰ بعدازظهر
    GOLD_24H = "gold_24h"       # ۲۴ ساعته (طلا/کالایی)
    CLOSED = "closed"           # خارج از ساعت معاملات


@dataclass(frozen=True)
class MarketSession:
    name: SessionName
    label: str
    start: time
    end: time
    days: list[int]  # ۰=شنبه ... ۴=چهارشنبه، ۵=جمعه (بازار بسته)


# جلسات استاندارد بازار ایران (شنبه تا چهارشنبه)
MARKET_SESSIONS: list[MarketSession] = [
    MarketSession(SessionName.PRE_OPEN, "پیش‌بازار (پیش‌سفارش)", time(8, 45), time(9, 0), [0, 1, 2, 3, 4]),
    MarketSession(SessionName.MORNING, "صبح بازار", time(9, 0), time(12, 0), [0, 1, 2, 3, 4]),
    MarketSession(SessionName.MIDDAY, "میانی بازار", time(11, 0), time(15, 0), [0, 1, 2, 3, 4]),
    MarketSession(SessionName.AFTERNOON, "بعدازظهر بازار", time(15, 0), time(17, 0), [0, 1, 2, 3, 4]),
    MarketSession(SessionName.GOLD_24H, "طلا/کالایی ۲۴ ساعته", time(0, 0), time(23, 59), [0, 1, 2, 3, 4, 5, 6]),
]


# نگاشت نوع صندوق به جلسه معاملاتی
FUND_SESSION_MAP: dict[str, SessionName] = {
    "طلا": SessionName.GOLD_24H,
    "کالایی": SessionName.GOLD_24H,
    "اهرم": SessionName.MORNING,
    "سهامی": SessionName.MORNING,
    "مختلط": SessionName.MORNING,
    "درآمد ثابت": SessionName.MIDDAY,
}


# زمان‌بندی گزارش‌های خودکار
REPORT_SCHEDULE: dict[str, dict] = {
    "08:50": {"name": "market_brief", "label": "صبحانه بازار", "session": SessionName.PRE_OPEN},
    "10:00": {"name": "micro_update", "label": "نبرد صبح", "session": SessionName.MORNING},
    "12:30": {"name": "midday_summary", "label": "استراحت بازار", "session": SessionName.MIDDAY},
    "15:15": {"name": "final_hour", "label": "ساعت آخر", "session": SessionName.AFTERNOON},
    "17:10": {"name": "market_close", "label": "بازار بسته", "session": SessionName.CLOSED},
    "18:00": {"name": "backtest_learn", "label": "بک‌تست و یادگیری", "session": SessionName.CLOSED},
}


class MarketHoursEngine:
    """موتور تعیین وضعیت بازار و جلسه فعلی."""

    def __init__(self, tz_offset_hours: float = 3.5) -> None:  # UTC+3:30 ایران
        self.tz_offset = tz_offset_hours

    def now_iran(self) -> datetime:
        """زمان فعلی ایران (UTC+3:30)."""
        utc_now = datetime.now(timezone.utc)
        from datetime import timedelta
        return utc_now + timedelta(hours=self.tz_offset)

    def get_current_session(self, dt: Optional[datetime] = None) -> MarketSession:
        """جلسه فعلی بازار را برمی‌گرداند."""
        dt = dt or self.now_iran()
        weekday = dt.weekday()  # ۰=دوشنبه در پایتون، تبدیل به ۰=شنبه
        iran_weekday = (weekday + 1) % 7  # ۰=شنبه، ۵=جمعه، ۶=شنبه
        current_time = dt.time()

        for session in MARKET_SESSIONS:
            if iran_weekday in session.days and session.start <= current_time < session.end:
                return session

        return MarketSession(SessionName.CLOSED, "بازار بسته", time(0, 0), time(0, 0), [])

    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        """آیا بازار باز است؟"""
        return self.get_current_session(dt).name != SessionName.CLOSED

    def get_fund_session(self, fund_type: str) -> SessionName:
        """جلسه معاملاتی مربوط به نوع صندوق."""
        return FUND_SESSION_MAP.get(fund_type, SessionName.MORNING)

    def is_fund_trading_now(self, fund_type: str, dt: Optional[datetime] = None) -> bool:
        """آیا این نوع صندوق الان در حال معامله است؟"""
        session = self.get_fund_session(fund_type)
        if session == SessionName.GOLD_24H:
            return True  # طلا/کالایی همیشه فعال (روزهای کاری)
        current = self.get_current_session(dt)
        return current.name in {SessionName.MORNING, SessionName.MIDDAY, SessionName.AFTERNOON}

    def next_report_time(self, dt: Optional[datetime] = None) -> Optional[str]:
        """زمان گزارش بعدی برنامه‌ریزی شده."""
        dt = dt or self.now_iran()
        current_minutes = dt.hour * 60 + dt.minute
        for time_str in sorted(REPORT_SCHEDULE.keys()):
            h, m = map(int, time_str.split(":"))
            if h * 60 + m > current_minutes:
                return time_str
        return None  # گزارش‌های امروز تمام شده

    def to_jalali_str(self, dt: Optional[datetime] = None) -> str:
        """تبدیل به تاریخ شمسی رشته‌ای."""
        dt = dt or self.now_iran()
        jd = jdatetime.date.fromgregorian(date=dt.date())
        return f"{jd.year:04d}/{jd.month:02d}/{jd.day:02d}"

    def to_jalali_full(self, dt: Optional[datetime] = None) -> str:
        """تاریخ و ساعت کامل شمسی."""
        dt = dt or self.now_iran()
        jd = jdatetime.datetime.fromgregorian(datetime=dt)
        return f"{jd.year:04d}/{jd.month:02d}/{jd.day:02d} {jd.hour:02d}:{jd.minute:02d}"


# Singleton instance
_market_hours = MarketHoursEngine()


def get_market_hours() -> MarketHoursEngine:
    return _market_hours


def current_session() -> MarketSession:
    return _market_hours.get_current_session()


def is_market_open() -> bool:
    return _market_hours.is_market_open()


def next_report() -> Optional[str]:
    return _market_hours.next_report_time()


def jalali_now() -> str:
    return _market_hours.to_jalali_full()