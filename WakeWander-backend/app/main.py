from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.routes import router
from app.core.database import engine
from app.models.models import Base

settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WakeWander Travel Planner API",
    description="AI-powered travel planning with Langgraph",
    version="1.0.0"
)

# CORS
cors_origins = settings.CORS_ORIGINS
if isinstance(cors_origins, str):
    if "," in cors_origins:
        cors_origins = [origin.strip().strip('"').strip("'") for origin in cors_origins.split(",")]
    elif cors_origins.startswith("["):
        import json
        cors_origins = json.loads(cors_origins)
    else:
        cors_origins = [cors_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

app.include_router(router, prefix="/api", tags=["travel"])


@app.get("/")
async def root():
    return {
        "message": "WakeWander Travel Planner API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
