# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # loads environment variables from a .env file if available

class Config:
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URI", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    RATELIMIT_DEFAULT: str = "5 per minute"
