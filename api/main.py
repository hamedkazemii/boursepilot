from fastapi import FastAPI

from api.routers import health, market, ranking, funds


app = FastAPI(
    title="Sandoghchi API",
    version="0.1.0",
    description="Backend API for Sandoghchi"
)


app.include_router(
    health.router,
    prefix="/api/v1"
)

app.include_router(
    market.router,
    prefix="/api/v1"
)

app.include_router(
    ranking.router,
    prefix="/api/v1"
)

app.include_router(
    funds.router,
    prefix="/api/v1"
)


@app.get("/")
def root():
    return {
        "name": "Sandoghchi",
        "status": "running"
    }
