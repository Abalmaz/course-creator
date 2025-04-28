#!/bin/bash

# Deployment script for AI Course Creator API
# This script sets up and starts the application in production mode

# Exit on error
set -e

echo "Starting AI Course Creator API deployment..."

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running database migrations..."
python manage.py migrate

# Start Celery worker in the background
echo "Starting Celery worker..."
celery -A ai_course_creator_project worker --loglevel=info --detach

# Start Gunicorn with the configuration file
echo "Starting Gunicorn server..."
gunicorn ai_course_creator_project.wsgi:application -c gunicorn.conf.py

echo "Deployment complete!"
