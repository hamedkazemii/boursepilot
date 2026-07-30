import unittest
from core.alerts.models import Alert
from core.alerts.engine import AlertEngine
from core.alerts.triggers.volume import VolumeAnomalyTrigger

class TestAlertsFoundation(unittest.TestCase):
    def test_volume_anomaly_trigger(self):
        trigger = VolumeAnomalyTrigger(threshold=1000)
        data = {"symbol": "AYAR", "volume": 1500}
        alert = trigger.evaluate(data)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.symbol, "AYAR")
        self.assertEqual(alert.alert_type, "volume_anomaly")

    def test_alert_engine(self):
        engine = AlertEngine()
        engine.register_trigger(VolumeAnomalyTrigger(threshold=1000))
        
        # Test case with anomaly
        data = {"symbol": "AYAR", "volume": 1500}
        alerts = engine.evaluate(data)
        self.assertEqual(len(alerts), 1)
        
        # Test case without anomaly
        data_clean = {"symbol": "AYAR", "volume": 500}
        alerts = engine.evaluate(data_clean)
        self.assertEqual(len(alerts), 0)

if __name__ == '__main__':
    unittest.main()
