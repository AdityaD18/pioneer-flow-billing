from fastapi import FastAPI
from config.settings import settings
from api.routes import health, company, sync, stock, ledgers

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Register API Routers at root level for canonical REST endpoints
app.include_router(health.router)
app.include_router(company.router)
app.include_router(stock.router)
app.include_router(ledgers.router)
app.include_router(sync.router)

# Also register under /api/v1 prefix for versioned clients
app.include_router(sync.router, prefix=settings.API_PREFIX)
app.include_router(stock.router, prefix=settings.API_PREFIX)
app.include_router(ledgers.router, prefix=settings.API_PREFIX)

@app.get("/")
def root():
    return {
        "service": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/company",
            "/stock",
            "/stock/groups",
            "/customers",
            "/ledgers",
            "/sync/status",
            "/sync/full",
            "/sync/incremental"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
