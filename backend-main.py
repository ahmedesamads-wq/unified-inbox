from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.config import settings
from src.database import engine, Base
from src.api.v1 import auth, accounts, messages, oauth


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up Unified Inbox API...")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Unified Inbox API",
    description="Self-hosted unified inbox for Gmail and Outlook",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(oauth.router, prefix="/api/v1/oauth", tags=["oauth"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "message": "Unified Inbox API",
        "version": "1.0.0",
        "docs": "/docs"
    }
