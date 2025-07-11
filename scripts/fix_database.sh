#!/bin/bash
# Fix database schema on server

echo "🔧 Fixing database schema..."

# Go to backend directory
cd /opt/review-platform/backend

# Activate virtual environment
source ../venv/bin/activate

# Stop the service
sudo systemctl stop review-platform

# Run migration script
python migrate_db.py

# If migration fails, recreate database
if [ $? -ne 0 ]; then
    echo "⚠️  Migration failed, recreating database..."
    rm -f sql_app.db
    python -c "
from app.db.database import engine
from app.db.models import Base
Base.metadata.create_all(bind=engine)
print('✅ Database recreated successfully')
"
fi

# Start the service
sudo systemctl start review-platform

echo "✅ Database fix completed!"
echo "📝 Check service status: sudo systemctl status review-platform"