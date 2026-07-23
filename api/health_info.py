from datetime import datetime


def health_payload():

    return {
        "status":"ok",
        "service":"sandoghchi-api",
        "timestamp":datetime.utcnow().isoformat()
    }
