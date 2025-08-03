from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.logging_config import setup_shared_logging
from .api import auth, decks, reviews, questions, documents, config, healthcare_templates, pipeline, projects, internal, dojo, project_management, project_stages, dojo_experiments, funding_stages
from .db.models import Base
from .db.database import engine

# Configure shared filesystem logging
logger = setup_shared_logging("backend")

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(decks.router, prefix=settings.API_V1_STR)
app.include_router(reviews.router, prefix=settings.API_V1_STR)
app.include_router(questions.router, prefix=settings.API_V1_STR)
app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(config.router, prefix=settings.API_V1_STR)
app.include_router(healthcare_templates.router, prefix=settings.API_V1_STR)
app.include_router(pipeline.router, prefix=settings.API_V1_STR)
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(internal.router, prefix=settings.API_V1_STR)
app.include_router(dojo.router, prefix=settings.API_V1_STR)
app.include_router(project_management.router, prefix=settings.API_V1_STR)
app.include_router(project_stages.router, prefix=settings.API_V1_STR)
app.include_router(dojo_experiments.router, prefix=settings.API_V1_STR)
app.include_router(funding_stages.router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Startup Review Platform API"}

@app.get("/api/health")
def health_check():
    logger.info(f"Health check accessed - Environment: {settings.ENVIRONMENT}")
    return {"status": "healthy", "environment": settings.ENVIRONMENT}