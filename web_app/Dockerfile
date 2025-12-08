# Use a lightweight Python image
FROM python:3.10-slim

# Install system dependencies required for building Python packages, pipenv, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv globally
RUN pip install pipenv

# Set working directory
WORKDIR /app

# Copy Pipenv files FIRST (to leverage Docker caching)
COPY Pipfile Pipfile.lock ./

# Install dependencies inside the container
# --deploy ensures pipenv uses Pipfile.lock exactly
RUN pipenv install --deploy --ignore-pipfile

# Copy the web_app source code into the container
COPY . ./

# Environment variable (overridden in docker-compose.prod.yml)
ENV API_BASE_URL=http://localhost:8001

# Flask listens on port 5000 by default
EXPOSE 5000

# Command to start the Flask app using Pipenv
CMD ["pipenv", "run", "python", "app.py"]
