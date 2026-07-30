import unittest
from services.providers.health import provider_health
from services.providers.reliability import reliable_provider
import time

class TestReliability(unittest.TestCase):
    def setUp(self):
        # Reset health for 'test_provider'
        provider_health.stats['test_provider'] = {"failures": 0, "open": False}
        self.call_count = 0

    def test_retry_success(self):
        @reliable_provider("test_provider")
        def success_func(self):
            self.call_count += 1
            return "ok"
        
        result = success_func(self)
        self.assertEqual(result, "ok")
        self.assertEqual(self.call_count, 1)
        self.assertTrue(provider_health.is_healthy("test_provider"))

    def test_circuit_breaker(self):
        # Force 5 failures
        for _ in range(5):
            provider_health.report_failure("test_provider")
        
        self.assertFalse(provider_health.is_healthy("test_provider"))
        
        @reliable_provider("test_provider")
        def fail_func(self):
            return "should not be called"
        
        # Should raise exception because it's unhealthy
        with self.assertRaises(Exception):
            fail_func(self)

if __name__ == '__main__':
    unittest.main()
