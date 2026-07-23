from api.routers import advisor
from api.routers import portfolio
from api.routers import funds
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


from api.routers.users import router as users_router
from api.routers.portfolio import router as portfolio_router
from api.routers.admin import router as admin_router

app.include_router(users_router)
app.include_router(portfolio_router)
app.include_router(admin_router)



from api.routers.auth import router as auth_router

app.include_router(auth_router)


app.include_router(funds.router)

app.include_router(portfolio.router)

app.include_router(advisor.router)

from api.routers import admin

app.include_router(admin.router)

from api.routers import ai

app.include_router(ai.router)

from api.routers import admin_ai

app.include_router(admin_ai.router)
