from fastapi import FastAPI
from app.core.config import Settings
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.chat_session import router as chat_session_router

def create_app() -> FastAPI:
    settings = Settings()
    
    app = FastAPI(
        title="Health Agent API",
        version="0.1.0",
        description="Backend API for Health Agent application"
    )
    
    # Include routers
    app.include_router(chat_router, prefix="/api", tags=["chat"])
    app.include_router(auth_router, prefix="/api", tags=["auth"])
    app.include_router(chat_session_router, prefix="/api", tags=["chat-session"])
    
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)