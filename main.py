"""
FastAPI main application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import llm_router, content_policy_router
from config import settings

# Create FastAPI app
app = FastAPI(
    title="Cybersecurity War Gaming Platform API",
    description="AI-powered cybersecurity training and war gaming platform",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(llm_router)
app.include_router(content_policy_router)

# Import scenarios, game, settings, and audit routers
from api.routers import scenarios_router, game_router, settings_router, audit_router, analytics_router, auth_router
app.include_router(scenarios_router)
app.include_router(game_router)
app.include_router(settings_router)
app.include_router(audit_router)
app.include_router(analytics_router)
app.include_router(auth_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Cybersecurity War Gaming Platform API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
