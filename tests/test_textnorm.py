"""تست نرمال‌سازی نماد فارسی/عربی."""

from __future__ import annotations

import unittest

from services.providers.textnorm import normalize_fa, normalize_symbol


class TestTextNorm(unittest.TestCase):
    def test_ye_kaf(self) -> None:
        arabic = "كاردان"  # ك عربی
        # اگر ي عربی باشد
        arabic_ye = "پاي"
        self.assertEqual(normalize_symbol(arabic), "کاردان")
        self.assertEqual(normalize_symbol(arabic_ye), "پای")

    def test_zwnj_and_space(self) -> None:
        self.assertEqual(normalize_fa("صندوق\u200cطلا"), "صندوق طلا")

    def test_strip(self) -> None:
        self.assertEqual(normalize_symbol("  عیار  "), "عیار")


if __name__ == "__main__":
    unittest.main()
