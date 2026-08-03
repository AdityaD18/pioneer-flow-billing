from fastapi import FastAPI
from config.settings import settings
from api.routes import health, company, sync, stock, ledgers, version_routes
from security import token_auth

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.1",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Register Routers
app.include_router(health.router)
app.include_router(company.router)
app.include_router(stock.router)
app.include_router(ledgers.router)
app.include_router(sync.router)
app.include_router(version_routes.router)
app.include_router(token_auth.router)

@app.get("/")
def root():
    return {
        "service": settings.APP_NAME,
        "version": "2.0.1",
        "protocol": 1,
        "status": "running",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/version",
            "/capabilities",
            "/identity",
            "/device/register",
            "/company",
            "/stock",
            "/stock/groups",
            "/customers",
            "/suppliers",
            "/ledgers",
            "/sync/status",
            "/sync/full",
            "/sync/incremental"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
