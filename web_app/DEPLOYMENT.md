# Deployment Guide – SWE Project 5

This document describes how the system is deployed to the DigitalOcean Droplet, how Docker is used for both the API and web application, and how to manually recover the services if CI/CD fails.

## 1. Architecture Overview

The system consists of two main components running on a single DigitalOcean Droplet:

- **API stack (`api`)**
  - Services: `search_api`, `clob_display`, `ws_clob`, and `redis`.
  - Deployed as a Docker Compose project.
  - Exposes ports `8001`, `8002`, and `8003` for different API services.

- **Web application (`web_app`)**
  - Flask-based frontend.
  - Deployed as a separate Docker Compose project.
  - Exposes HTTP on port `80` (mapped to container port `5000`).

- **Database**
  - MongoDB Atlas (managed external cluster).
  - Accessed by the API via `MONGO_URI` and related environment variables.
  - No MongoDB container runs on the Droplet.

## 2. File and Directory Layout on the Droplet

All deployment-related files on the Droplet live under `/opt/project_5`:

- `/opt/project_5/.env`
  - Shared environment file containing sensitive configuration (MongoDB credentials, secret keys).

- `/opt/project_5/api`
  - Production Docker Compose file for the API stack:
    - `docker-compose.prod.yml`

- `/opt/project_5/web_app`
  - Production Docker Compose file for the web application:
    - `docker-compose.prod.yml`

### 2.1 Corresponding files in the GitHub repository

- `api/docker-compose.prod.yml`
  - Template used to provision `/opt/project_5/api/docker-compose.prod.yml`.

- `web_app/docker-compose.prod.yml`
  - Template used to provision `/opt/project_5/web_app/docker-compose.prod.yml`.

- `.github/workflows/api-ci.yml`
  - CI/CD workflow for building and deploying API images.

- `.github/workflows/web-app-ci.yml`
  - CI/CD workflow for building and deploying the web application image.

## 3. Environment Variables and Secrets

The Droplet uses a single shared `.env` file:

- Path: `/opt/project_5/.env`

This file is referenced by the `env_file` directive in both Compose projects and is not committed to the repository. It must define at least:

- `MONGO_URI`  
- `MONGO_DB`  
- `MONGO_USER`  
- `MONGO_PASS`  
- `SECRET_KEY`  

Additional variables may be added if the application code is extended, but these are the core values required for:

- API access to MongoDB Atlas.
- Flask application secret key (sessions/CSRF/etc.).

### 3.1 How env vars are injected

- **API stack (`/opt/project_5/api/docker-compose.prod.yml`)**  
  - Each API service that talks to MongoDB includes:
    ```yaml
    env_file:
      - /opt/project_5/.env
    ```
  - The API code reads values using `os.environ` (e.g. `os.environ["MONGO_URI"]`).

- **Web application (`/opt/project_5/web_app/docker-compose.prod.yml`)**  
  - The web_app service also includes:
    ```yaml
    env_file:
      - /opt/project_5/.env
    environment:
      FLASK_ENV: "production"
      API_BASE_URL: "http://64.225.22.79:8001"
    ```
  - `SECRET_KEY` and any other shared values are read from `os.environ` in the Flask code.

## 4. CI/CD Overview

Deployment is handled by GitHub Actions for both the API and web application.

### 4.1 API CI/CD (`api-ci.yml`)

On pushes to `main`:

1. Linting/tests are run for the API code.
2. Docker images (e.g. `search_api`, `clob_display`, `ws_clob`) are built and pushed to Docker Hub under the configured Docker Hub username.
3. An SSH step connects to the Droplet and executes:
   ```bash
   cd /opt/project_5/api
   docker-compose -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.prod.yml up -d
