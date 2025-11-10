from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.config import settings
from src.database import engine, Base
from src.api.v1 import auth, accounts, messages, oauth

# [Rest of the FastAPI main.py content]