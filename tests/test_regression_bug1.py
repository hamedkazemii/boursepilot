import unittest
from core.scoring.models import FundAssessment
from services.telegram.smart_report import format_fund_card
from config import settings

class TestSmartReportBug1(unittest.TestCase):
    def test_format_fund_card_no_error(self):
        # Mock FundAssessment
        a = FundAssessment(
            symbol="test",
            name="test fund",
            fund_type="سهامی",
            final_score=70.0,
            rank=1,
            recommendation_label="جذاب",
            factors=[],
            ins_code="123456",
            sector="سهامی",
            recommendation="BUY"
        )
        # Should not raise NameError: name 'product' is not defined
        try:
            result = format_fund_card(a, kind="top")
            self.assertIn(settings.PRODUCT_NAME, result)
        except NameError as e:
            self.fail(f"format_fund_card raised NameError unexpectedly: {e}")

if __name__ == '__main__':
    unittest.main()
