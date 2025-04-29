import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-should-be-changed')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/images/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    # Use a single database URI for all environments
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://localhost/lunchapp2')

class DevelopmentConfig(Config):
    DEBUG = True

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': DevelopmentConfig,
    'testing': DevelopmentConfig,
    'default': DevelopmentConfig
} 