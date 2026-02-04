"""
Configuration file for IPC database project
Loads credentials from environment variables for security
"""

import os
from dotenv import load_dotenv
import urllib.parse

# Load environment variables from .env file
load_dotenv()

class Config:
    """Database and application configuration"""
    
    # Database credentials
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT', '6543')
    DB_NAME = os.getenv('DB_NAME', 'postgres')
    
    # Data configuration
    START_DATE = os.getenv('START_DATE', '2023-12-01')
    
    @classmethod
    def get_db_url(cls):
        """
        Constructs the database URL with properly encoded password
        """
        if not all([cls.DB_USER, cls.DB_PASSWORD, cls.DB_HOST]):
            raise ValueError(
                "Missing required environment variables. "
                "Please ensure DB_USER, DB_PASSWORD, and DB_HOST are set in .env file"
            )
        
        safe_password = urllib.parse.quote_plus(cls.DB_PASSWORD)
        return f"postgresql+psycopg2://{cls.DB_USER}:{safe_password}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    @classmethod
    def validate(cls):
        """
        Validates that all required configuration is present
        """
        required_vars = ['DB_USER', 'DB_PASSWORD', 'DB_HOST']
        missing = [var for var in required_vars if not getattr(cls, var)]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Please create a .env file based on .env.example"
            )
        
        return True
