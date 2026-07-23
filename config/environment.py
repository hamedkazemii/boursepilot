import os


class Settings:

    APP_NAME = os.getenv(
        "APP_NAME",
        "sandoghchi-api"
    )

    ENVIRONMENT = os.getenv(
        "ENVIRONMENT",
        "development"
    )

    DEBUG = os.getenv(
        "DEBUG",
        "false"
    ).lower() == "true"

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///data/database.db"
    )

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "change-this-secret"
    )


settings = Settings()
