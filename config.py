"""
Configuration file for IPC database project
Loads credentials from environment variables for security
"""

import os
from dotenv import load_dotenv
import urllib.parse

# Load environment variables from .env file for local development
load_dotenv()

class Config:
    """
    Database and application configuration management.
    Prioritizes system environment variables (useful for GitHub Actions) 
    over local .env files.
    """
    
    # Database credentials fetched from environment variables
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = os.environ.get('DB_PORT', '6543')
    DB_NAME = os.environ.get('DB_NAME', 'postgres')
    
    # Default start date for initial data extraction
    START_DATE = os.environ.get('START_DATE', '2023-12-01')
    
    @classmethod
    def get_db_url(cls):
        """
        Constructs the SQLAlchemy database connection string.
        Handles special characters in passwords using URL encoding.
        """
        # Re-check variables to ensure they are captured during runtime
        user = cls.DB_USER or os.environ.get('DB_USER')
        password = cls.DB_PASSWORD or os.environ.get('DB_PASSWORD')
        host = cls.DB_HOST or os.environ.get('DB_HOST')
        
        if not all([user, password, host]):
            raise ValueError(
                "Connection Error: DB_USER, DB_PASSWORD, or DB_HOST are not defined. "
                "Verify GitHub Secrets or your local .env file."
            )
        
        # URL-encode password to handle special characters (like '@' or ':')
        safe_password = urllib.parse.quote_plus(password)
        
        return f"postgresql+psycopg2://{user}:{safe_password}@{host}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    @classmethod
    def validate(cls):
        """
        Validates that all strictly required configuration variables are present.
        Returns True if valid, raises ValueError otherwise.
        """
        required_vars = {
            'DB_USER': cls.DB_USER or os.environ.get('DB_USER'),
            'DB_PASSWORD': cls.DB_PASSWORD or os.environ.get('DB_PASSWORD'),
            'DB_HOST': cls.DB_HOST or os.environ.get('DB_HOST')
        }
        
        missing = [var for var, value in required_vars.items() if not value]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Action required: Set these variables in GitHub Secrets or a local .env file."
            )
        
        return True