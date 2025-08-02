from app.core.config import settings
print('DATABASE_URL:', settings.DATABASE_URL)
print('Environment file exists:', __import__('os').path.exists('.env'))
