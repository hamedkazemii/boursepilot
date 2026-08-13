from services.telegram.publisher import publish_message

class DevelopmentReporter:
    @staticmethod
    def send_report(report_text: str):
        # Using existing telegram publisher to send dev updates
        publish_message(f"🤖 BoursePilot Dev Report:\n\n{report_text}")
