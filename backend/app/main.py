from fastapi import FastAPI
from .core.config import Settings
from .api.health import router as health_router
from .api.chat import router as chat_router
from .api.retrieval import router as retrieval_router

def create_app() -> FastAPI:
    settings = Settings()
    
    app = FastAPI(
        title="Health Agent API",
        version="0.1.0",
        description="Backend API for Health Agent application"
    )
    
    # Include routers
    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(chat_router, prefix="/api", tags=["chat"])
    app.include_router(retrieval_router, prefix="/api", tags=["retrieval"])
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)