import os

class Config:
    # Use environment variables or defaults for development
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///default.db')  # Provide a default URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', b'\xf7\xb1}\xf3T"\x8a\x95\xf3{\x01\x0c\x82\xab\x84\xc4\xac\xfe1\x11\x14\x7f\x8b\xb4')