from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from .core.config import settings
from .core.logging_config import setup_shared_logging
from .api import auth, decks, reviews, questions, documents, documents_robust, config, healthcare_templates, pipeline, projects, internal, dojo, project_management, project_stages, dojo_experiments, funding_stages, invitations, feedback
from .db.models import Base
from .db.database import engine
from .services.queue_processor import queue_processor

# Configure shared filesystem logging
logger = setup_shared_logging("backend")

# Create database tables
Base.metadata.create_all(bind=engine)

# Background task for queue processing
background_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global background_task
    logger.info("Starting queue processor background task")
    background_task = asyncio.create_task(queue_processor.start())
    yield
    # Shutdown
    logger.info("Stopping queue processor background task")
    await queue_processor.stop()
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

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
app.include_router(documents_robust.router, prefix=f"{settings.API_V1_STR}/robust")
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
app.include_router(invitations.router, prefix=settings.API_V1_STR)
app.include_router(feedback.router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Startup Review Platform API"}

@app.get("/api/health")
def health_check():
    logger.info(f"Health check accessed - Environment: {settings.ENVIRONMENT}")
    return {"status": "healthy", "environment": settings.ENVIRONMENT}