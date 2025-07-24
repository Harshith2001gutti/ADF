"""
Configuration settings for Action Item Tracker
This file contains configuration classes for different environments.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class."""
    
    # Application settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database settings
    DB_SERVER = os.getenv('DB_SERVER', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'ActionItemDB')
    DB_USERNAME = os.getenv('DB_USERNAME', 'sa')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'YourPassword123')
    DB_DRIVER = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    
    # SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = (
        f'mssql+pyodbc://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}'
        f'?driver={DB_DRIVER}&TrustServerCertificate=yes'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Flask settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Application settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # Email settings (for future notifications)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@actiontracker.com')

class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    TESTING = False
    
    # Development database (can use different database for dev)
    DB_NAME = os.getenv('DEV_DB_NAME', Config.DB_NAME)
    
    # Override SQLAlchemy URI for development
    SQLALCHEMY_DATABASE_URI = (
        f'mssql+pyodbc://{Config.DB_USERNAME}:{Config.DB_PASSWORD}@{Config.DB_SERVER}/{DB_NAME}'
        f'?driver={Config.DB_DRIVER}&TrustServerCertificate=yes'
    )
    
    # Development-specific settings
    SQLALCHEMY_ECHO = True  # Log SQL queries in development
    WTF_CSRF_ENABLED = False  # Disable CSRF for easier development

class TestingConfig(Config):
    """Testing configuration."""
    
    TESTING = True
    DEBUG = True
    
    # Use separate test database
    DB_NAME = os.getenv('TEST_DB_NAME', 'ActionItemDB_Test')
    
    SQLALCHEMY_DATABASE_URI = (
        f'mssql+pyodbc://{Config.DB_USERNAME}:{Config.DB_PASSWORD}@{Config.DB_SERVER}/{DB_NAME}'
        f'?driver={Config.DB_DRIVER}&TrustServerCertificate=yes'
    )
    
    # Testing-specific settings
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'

class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Production security settings
    SESSION_COOKIE_SECURE = True  # Requires HTTPS
    PREFERRED_URL_SCHEME = 'https'
    
    # Production database settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20,
    }
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'action_tracker.log')

class DockerConfig(Config):
    """Docker container configuration."""
    
    DEBUG = False
    
    # Docker-specific database settings
    DB_SERVER = os.getenv('DB_SERVER', 'db')  # Docker service name
    
    SQLALCHEMY_DATABASE_URI = (
        f'mssql+pyodbc://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}/{Config.DB_NAME}'
        f'?driver={Config.DB_DRIVER}&TrustServerCertificate=yes'
    )

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'docker': DockerConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment variable."""
    env = os.getenv('FLASK_ENV', 'development').lower()
    return config.get(env, config['default'])

# Database connection helper
def get_database_url():
    """Get database URL for current environment."""
    config_class = get_config()
    return config_class.SQLALCHEMY_DATABASE_URI

# Validation functions
def validate_config():
    """Validate configuration settings."""
    errors = []
    
    # Check required environment variables
    required_vars = ['DB_SERVER', 'DB_NAME', 'DB_USERNAME', 'DB_PASSWORD']
    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"Missing required environment variable: {var}")
    
    # Check secret key in production
    if os.getenv('FLASK_ENV') == 'production' and os.getenv('SECRET_KEY') == 'dev-secret-key-change-in-production':
        errors.append("SECRET_KEY must be changed in production")
    
    return errors

# Utility functions
def is_development():
    """Check if running in development mode."""
    return os.getenv('FLASK_ENV', 'development').lower() == 'development'

def is_production():
    """Check if running in production mode."""
    return os.getenv('FLASK_ENV', 'development').lower() == 'production'

def is_testing():
    """Check if running in testing mode."""
    return os.getenv('FLASK_ENV', 'development').lower() == 'testing'