import os
import secrets
from datetime import timedelta

class Config:
    """Base configuration"""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///vaccination.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Use a fixed fallback for dev to avoid invalidating sessions on reload
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-static-secret-key-12345'
    
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
