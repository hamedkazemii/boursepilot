import sys
from unittest.mock import MagicMock
sys.modules['config'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

import unittest
from unittest.mock import MagicMock
from services.providers.reliability import reliable_provider
from services.providers.exceptions import ProviderAuthError

class TestReliability(unittest.TestCase):
    def setUp(self):
        self.mock_provider = MagicMock()
        self.mock_provider.name = "test_provider"

    def test_retry_on_failure(self):
        # Mocking a provider without fallback_get_json
        mock_no_fallback = MagicMock()
        del mock_no_fallback.fallback_get_json
        
        @reliable_provider("test_provider")
        def failing_func(self):
            raise Exception("Transient error")

        with self.assertRaises(Exception):
            failing_func(mock_no_fallback)

    def test_auth_fail_fast(self):
        @reliable_provider("test_provider")
        def auth_fail_func(self):
            raise ProviderAuthError("Auth error")

        with self.assertRaises(ProviderAuthError):
            auth_fail_func(self.mock_provider)

    def test_fallback_execution(self):
        mock_with_fallback = MagicMock()
        mock_with_fallback.fallback_get_json.return_value = "fallback_result"
        
        @reliable_provider("test_provider")
        def failing_func(self):
            raise Exception("Transient error")

        result = failing_func(mock_with_fallback)
        self.assertEqual(result, "fallback_result")

if __name__ == '__main__':
    unittest.main()
