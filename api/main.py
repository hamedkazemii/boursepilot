from fastapi import FastAPI

from api.routers import (
    health,
    market,
    ranking,
    funds,
    auth,
    users,
    portfolio,
    advisor,
    admin,
    ai,
    admin_ai
)


app = FastAPI(
    title="Sandoghchi API",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "service": "sandoghchi",
        "status": "running"
    }


# Core API









# Admin



# AI


# ROUTER_REGISTRATION_START

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
    prefix="/api/v1/ranking"
)

app.include_router(
    funds.router,
    prefix="/api/v1"
)

app.include_router(
    auth.router,
    prefix="/api/v1/auth"
)

app.include_router(
    users.router,
    prefix="/api/v1"
)

app.include_router(
    portfolio.router,
    prefix="/api/v1"
)

app.include_router(
    advisor.router,
    prefix="/api/v1"
)

app.include_router(
    admin.router,
    prefix="/admin"
)

app.include_router(
    admin_ai.router,
    prefix="/admin/ai"
)

app.include_router(
    ai.router,
    prefix="/ai"
)

# ROUTER_REGISTRATION_END
