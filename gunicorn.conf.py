# Gunicorn Configuration File
# For more information, see: https://docs.gunicorn.org/en/stable/configure.html

import multiprocessing

# Bind to 0.0.0.0:8000
bind = "0.0.0.0:8000"

# Number of worker processes
# A good rule of thumb is 2-4 x number of CPU cores
workers = multiprocessing.cpu_count() * 2 + 1

# Worker class
worker_class = "sync"

# Timeout (in seconds)
timeout = 120

# Access log file
accesslog = "-"  # Log to stdout

# Error log file
errorlog = "-"  # Log to stderr

# Log level
loglevel = "info"

# Process name
proc_name = "ai_course_creator"

# Preload application code before forking workers
preload_app = True

# Maximum number of requests a worker will process before restarting
max_requests = 1000
max_requests_jitter = 50  # Add jitter to max_requests to avoid all workers restarting at once

# Graceful timeout (in seconds)
graceful_timeout = 30

# Keep the connection alive for requests from the same client (seconds)
keepalive = 5
