# Final Project - MostEpicest

# Poly Paper

Poly Paper is a paper-trading web application built on top of Polymarket’s public APIs. It enables users to register, log in, browse prediction markets, and (in future iterations) simulate trading activity without using real funds. The system is composed of two major components:

- **Web Application (`web_app/`)** — A Flask-based interface that manages users, sessions, authentication, and the UI.
- **API Layer (`api/`)** — A set of FastAPI microservices that provide market search, CLOB price retrieval, and WebSocket-based real-time data, all backed by Redis caching.

Poly Paper is designed as a modular system where the UI interacts with separate, containerized services that proxy and cache Polymarket data. This separation enables flexible scaling, clearer responsibility boundaries, and an easier path for future extensions to full paper-trade simulation.

# SECTION 2 — FEATURES AND HOW TO USE THE PROJECT

## Web Application (web_app/)

### Capabilities:
* User registration, login, logout.
* Password hashing with bcrypt.
* Session handling with Flask-Login.
* User data stored in MongoDB.
* Included pages:
  * `/register`
  * `/login`
  * `/portfolio` (mock data)
  * `/markets` (mock data)
  * `/markets/<id>` (mock data)
  * `/settings` (username update)

### Run the web app locally:
```bash
cd web_app
pipenv install --dev
pipenv run python app.py
```

The app becomes available at: `http://127.0.0.1:5000`

## API Layer (api/)

The project contains three FastAPI microservices, each running in its own container.

### 1. Search API — search_api.py
**Example request:** `http://localhost:8001/search?q=btc&page=1`

**Function:**
* Proxies Polymarket's official search endpoint.
* Caches responses in Redis.

### 2. CLOB Display API — clob_display.py
**Example request:** `http://localhost:8002/clob?tokens=123,456`

**Function:**
* Fetches CLOB prices using py_clob_client.
* Uses retry logic plus Redis caching.

### 3. WebSocket CLOB API — ws_clob.py
**Function:**
* Exposes a WebSocket server on port 8003 for future real-time updates.

### Run all API services locally:
```bash
cd api
docker compose up --build
```

### After startup:
* Redis runs at `localhost:6379`
* Search API runs at `localhost:8001`
* CLOB API runs at `localhost:8002`
* WebSocket API runs at `localhost:8003`

### Quick smoke tests:
```bash
curl "http://localhost:8001/search?q=btc&page=1"
curl "http://localhost:8002/clob?tokens=123"
```

## Environment Variables

A `.env` file must exist at the repository root (or be mounted in Docker).

**Example .env:**
```
MONGO_URI=mongodb+srv://yourcluster/polypaper
SECRET_KEY=dev-secret-key
API_BASE_URL=http://localhost:8001
```

## Dependencies

### Primary libraries:
* Flask, Flask-Login, Flask-Bcrypt
* FastAPI, Uvicorn
* Redis, aiocache
* py_clob_client
* Pipenv for dependency management in web_app/

### Install dependencies for the web app:
```bash
cd web_app
pipenv install
```

# SECTION 3 — ARCHITECTURE OVERVIEW

## System Overview

Poly Paper is built as a multi-service application with a clear separation between the user-facing interface and the market data backend. The system is composed of:

1. A Flask web application that handles user authentication, sessions, routing, HTML rendering, and communication with backend APIs.
2. A group of FastAPI microservices that act as an intermediary between the web app and Polymarket's public APIs.
3. A Redis instance used as a shared caching layer across the API services.
4. A MongoDB database that stores user records for authentication and settings.

This modular architecture allows each component to be developed, deployed, and scaled independently.

## Component Responsibilities

### Web Application (web_app/):
* Manages user sign-up, login, logout, and settings updates.
* Serves HTML templates for markets, portfolio, and user settings.
* Stores and retrieves user data through MongoDB.
* Communicates with the API layer for future live market data integration through HTTP requests.

### Search API (api/search_api.py):
* Provides an endpoint that proxies Polymarket's search results.
* Uses Redis to cache queries for improved speed and reduced external API calls.
* Accepts parameters such as search terms and pagination.

### CLOB Display API (api/clob_display.py):
* Retrieves price data from Polymarket's CLOB (central limit order book).
* Uses the py_clob_client library to fetch best bid/ask or mid-price.
* Caches results in Redis for short durations.
* Implements retry logic for reliability.

### WebSocket CLOB API (api/ws_clob.py):
* Provides a WebSocket endpoint intended for real-time CLOB updates.
* Runs independently from the other two API services.
* Designed for future integration into the web interface.

## Supporting Infrastructure

### Redis:
* Shared caching backend for all API services.
* Configured with memory limits and LRU eviction.

### MongoDB:
* Stores all user account data, including hashed passwords and metadata.

### Docker and Container Layout:
* Each API microservice has its own Dockerfile.
* A separate Dockerfile is used for the web application.
* docker-compose files define local and production deployments for both the API layer and the web app.

## Data Flow Summary

1. The user interacts with the Flask frontend through a browser.
2. The frontend performs authentication and serves pages from the server.
3. When market data is needed, the frontend will send HTTP requests (or future WebSocket connections) to the API microservices.
4. The API services request fresh data from Polymarket or return cached versions from Redis.
5. The data flows back to the frontend for rendering.

This separation allows the system to support real-time market data, caching, and independent scaling of components without overloading the user-facing application.

# SECTION 4 — REPOSITORY STRUCTURE

## Overview

The repository is organized into two primary subsystems:

1. **web_app** — a Flask application responsible for user authentication, page rendering, and future interaction with backend APIs.
2. **api** — a collection of FastAPI microservices providing Polymarket market search, CLOB price retrieval, and WebSocket-based real-time data.

Additional folders support deployment, CI/CD, environment configuration, and project-wide dependency management.

## Directory Breakdown

### Root Directory:
* `.env` — Environment variables for local development (not for production use).
* `.env.prod` — Example or actual production environment file if provided separately.
* `.gitignore` — Git ignored files configuration.
* `LICENSE` — Project license.
* `README.md` — Main project documentation.
* `pyproject.toml` — pytest configuration at the repository root.
* `Pipfile`, `Pipfile.lock` — Root-level dependencies if applicable.

### web_app/ (Flask Application):
* `app.py` — Main Flask entrypoint. Handles routing, authentication, MongoDB access, and page rendering.
* `templates/` — HTML templates for login, registration, portfolio, markets, settings, and shared layouts.
* `static/` — CSS and JavaScript files used by the UI.
* `tests/` — Test suite for verifying web routes and functionality.
* `Dockerfile` — Container definition for the web app.
* `docker-compose.prod.yml` — Production docker-compose file for deployment.
* `env.example` — Example environment configuration.

### api/ (FastAPI Microservices):
* `search_api.py` — Microservice that proxies Polymarket's search endpoint and uses Redis caching.
* `clob_display.py` — Microservice that queries Polymarket's CLOB for price data.
* `ws_clob.py` — WebSocket server intended for real-time Polymarket CLOB updates.
* `requirements.txt` — Python dependencies for all API services.
* `Dockerfile.search`, `Dockerfile.clob`, `Dockerfile.ws` — Dockerfiles for each API microservice.
* `docker-compose.yml` — Local development stack including Redis and all API services.
* `docker-compose.prod.yml` — Production deployment definition.
* `tests/` — Test suite for API unit and integration tests.

### .github/workflows/ (CI/CD Pipelines):
* `web-app-ci.yml` — Pipeline for testing, building, and deploying the Flask web app.
* `api-ci.yml` — Pipeline for testing, building, and deploying the API microservices.
* `event-logger.yml` — Additional automated GitHub workflow if required.

### Other Supporting Files:
* `instructions.md` — Internal or development notes.
* `DEPLOYMENT.md` — Additional deployment documentation if included.
* `.githooks/` — Optional custom Git hooks such as commit message checks.

## High-Level Structure Summary

```
web_app/     → Flask server, HTML templates, and static assets
api/         → Search, CLOB, and WebSocket microservices
.github/     → CI/CD pipelines
Root         → Environment files, shared configs, general documentation
```

# SECTION 5 — INSTALLATION AND SETUP

This section explains how to set up Poly Paper for local development, including preparing the environment, installing dependencies, and running all services.

## Prerequisites

Before running the project locally, install the following:

* Python 3.10+ (for web_app) and Python 3.11+ (for API services)
* Pipenv (for managing Python environments in web_app)
* Docker and Docker Compose (for the API microservices and Redis)
* A local or cloud-hosted MongoDB instance

If MongoDB is not installed locally, you may use MongoDB Atlas and update your `.env` accordingly.

## Create Environment File

At the root directory, create a `.env` file if one does not exist.

**Example `.env`:**
```
MONGO_URI=mongodb://localhost:27017/polypaper
SECRET_KEY=dev-secret-key
API_BASE_URL=http://localhost:8001
```

**Note:**
* Use a secure secret key for production.
* API_BASE_URL refers to the Search API endpoint during development.

## Setup: Web Application (Flask)

Navigate to the Flask app directory:

```bash
cd web_app
```

Install dependencies with Pipenv:

```bash
pipenv install --dev
```

Run the server:

```bash
pipenv run python app.py
```

The web app becomes available at:

```
http://127.0.0.1:5000
```

## Setup: API Layer (FastAPI Microservices)

Navigate to the API directory:

```bash
cd api
```

Start all API services (Search API, CLOB API, WebSocket API) along with Redis:

```bash
docker compose up --build
```

Services will start at:
* Search API → `http://localhost:8001`
* CLOB Display API → `http://localhost:8002`
* WebSocket API → `ws://localhost:8003`
* Redis → `localhost:6379`

## Quick Tests

### Verify Search API:

```bash
curl "http://localhost:8001/search?q=btc&page=1"
```

### Verify CLOB API:

```bash
curl "http://localhost:8002/clob?tokens=123"
```

If both commands return structured JSON, the API layer is functioning correctly.

### Verify Web App connectivity:

Open `http://127.0.0.1:5000` in a browser and test login/registration pages.

# SECTION 5 — INSTALLATION AND SETUP

This section explains how to set up Poly Paper for local development, including preparing the environment, installing dependencies, and running all services.

## Prerequisites

Before running the project locally, install the following:

* Python 3.10+ (for web_app) and Python 3.11+ (for API services)
* Pipenv (for managing Python environments in web_app)
* Docker and Docker Compose (for the API microservices and Redis)
* A local or cloud-hosted MongoDB instance

If MongoDB is not installed locally, you may use MongoDB Atlas and update your `.env` accordingly.

## Create Environment File

At the root directory, create a `.env` file if one does not exist.

**Example `.env`:**
```
MONGO_URI=mongodb://localhost:27017/polypaper
SECRET_KEY=dev-secret-key
API_BASE_URL=http://localhost:8001
```

**Note:**
* Use a secure secret key for production.
* API_BASE_URL refers to the Search API endpoint during development.

## Setup: Web Application (Flask)

Navigate to the Flask app directory:

```bash
cd web_app
```

Install dependencies with Pipenv:

```bash
pipenv install --dev
```

Run the server:

```bash
pipenv run python app.py
```

The web app becomes available at:

```
http://127.0.0.1:5000
```

## Setup: API Layer (FastAPI Microservices)

Navigate to the API directory:

```bash
cd api
```

Start all API services (Search API, CLOB API, WebSocket API) along with Redis:

```bash
docker compose up --build
```

Services will start at:
* Search API → `http://localhost:8001`
* CLOB Display API → `http://localhost:8002`
* WebSocket API → `ws://localhost:8003`
* Redis → `localhost:6379`

## Quick Tests

### Verify Search API:

```bash
curl "http://localhost:8001/search?q=btc&page=1"
```

### Verify CLOB API:

```bash
curl "http://localhost:8002/clob?tokens=123"
```

If both commands return structured JSON, the API layer is functioning correctly.

### Verify Web App connectivity:

Open `http://127.0.0.1:5000` in a browser and test login/registration pages.

# SECTION 6 — ENVIRONMENT VARIABLES

This section lists the environment variables required for the system to function correctly across the web application, the API microservices, and production deployments.

## Overview

Environment variables are loaded from a `.env` file at the repository root for local development. In production, each Docker service loads variables via `env_file` in the corresponding `docker-compose.prod.yml`.

## Core Variables (Root-Level `.env`)

These variables apply to the Flask web application and are also referenced by API services when necessary.

```
MONGO_URI=<connection-string>
SECRET_KEY=<flask-secret-key>
API_BASE_URL=http://localhost:8001
```

**Explanation:**
* `MONGO_URI`: URI for the MongoDB instance where user data is stored.
* `SECRET_KEY`: Used by Flask to manage session signing and security.
* `API_BASE_URL`: Where the web app expects to reach the Search API (change in production).

**Optional (depending on your MongoDB setup):**

```
MONGO_USER=<username>
MONGO_PASS=<password>
```

## API Services Environment Variables

Each FastAPI microservice uses a consistent set of variables, often injected via Docker:

```
REDIS_HOST=redis
REDIS_PORT=6379
```

These variables inform the microservices where Redis is running. When running locally with Docker Compose, `redis` resolves automatically via Docker's internal network.

## Production Environment Variables

In production, the following are typically set via:
* `/opt/project_5/.env` on the server
* `docker-compose.prod.yml` under `env_file`

Variables include:

```
MONGO_URI=<remote-mongodb>
SECRET_KEY=<prod-secret>
API_BASE_URL=http://<server-ip>:8001
REDIS_HOST=redis
REDIS_PORT=6379
```

Web App (`web_app/docker-compose.prod.yml`) adds:

```
FLASK_ENV=production
```

API Services (`api/docker-compose.prod.yml`) automatically load:

```
REDIS_HOST
REDIS_PORT
```

## Best Practices

1. Never commit actual production `.env` files to the repository.
2. Use separate `.env`, `.env.staging`, and `.env.prod` files for different environments.
3. Keep `SECRET_KEY` and database credentials unique per environment.

# SECTION 7 — RUNNING THE SYSTEM

This section explains how to run all components of Poly Paper together, both locally and in a Docker-based workflow.

## Running the Web Application (Flask)

1. Navigate to the web_app directory:
   ```bash
   cd web_app
   ```

2. Install dependencies:
   ```bash
   pipenv install --dev
   ```

3. Start the Flask server:
   ```bash
   pipenv run python app.py
   ```

4. Visit the application in a browser:
   ```
   http://127.0.0.1:5000
   ```

**Pages you can test:**
* `/register`
* `/login`
* `/portfolio`
* `/markets`
* `/settings`

## Running the API Layer (FastAPI Services)

The API layer includes the Search API, CLOB Display API, and WebSocket CLOB API.

1. Navigate to the api directory:
   ```bash
   cd api
   ```

2. Start all API services and Redis:
   ```bash
   docker compose up --build
   ```

   This brings up:
   * Search API → `http://localhost:8001`
   * CLOB Display API → `http://localhost:8002`
   * WebSocket API → `ws://localhost:8003`
   * Redis → `localhost:6379`

3. Test endpoints:
   ```bash
   curl "http://localhost:8001/search?q=btc&page=1"
   curl "http://localhost:8002/clob?tokens=123"
   ```

## Running the Web App with the API Layer

The web app will use `API_BASE_URL` from your root `.env`:

**Example:**
```
API_BASE_URL=http://localhost:8001
```

**Ensure:**
* The API layer is running (ports 8001–8003)
* The web_app Flask server is running (port 5000)

The two pieces operate independently but communicate through HTTP.

## Full Local Setup Summary

1. **Start API layer:**
   ```bash
   cd api
   docker compose up --build
   ```

2. **Start web application:**
   ```bash
   cd web_app
   pipenv install --dev
   pipenv run python app.py
   ```

3. **Open browser and use the application normally.**

## When to Use Docker for the Web App

If preferred, the web app can also run inside Docker:

```bash
cd web_app
docker build -t poly-paper-web .
docker run --env-file ../.env -p 5000:5000 poly-paper-web
```

However, most developers work with Flask directly using Pipenv during development.

# SECTION 8 — DOCKER DEPLOYMENT

This section describes how Poly Paper is deployed using Docker and docker-compose in both the API layer and the web application. This includes the purpose of each Dockerfile and how containers run together in production.

## Docker Deployment: API Layer

Located in the `api/` directory, the API layer has three microservices, each with its own Dockerfile:

### 1. Dockerfile.search
* Builds the Search API (search_api.py).
* Installs dependencies from requirements.txt.
* Starts a Uvicorn server on port 8001.

### 2. Dockerfile.clob
* Builds the CLOB Display API (clob_display.py).
* Similar to the Search API image but starts on port 8002.

### 3. Dockerfile.ws
* Builds the WebSocket CLOB API (ws_clob.py).
* Starts a Uvicorn WebSocket server on port 8003.

Redis is also included in the docker-compose stack and is required for caching.

**Local development deployment:**
```bash
cd api
docker compose up --build
```

**Production deployment uses the file:**
```
api/docker-compose.prod.yml
```

This file pulls prebuilt images, for example:
```
danielleesignup/api-search_api:latest
danielleesignup/api-clob_display:latest
danielleesignup/api-ws_clob:latest
```

Redis is included in production as well.

## Docker Deployment: Web Application

Located in the `web_app/` directory, the web application has its own Dockerfile.

**Key points:**
* Uses `python:3.10-slim` as the base image.
* Installs system build tools and pipenv.
* Installs dependencies using Pipfile.lock.
* Copies in the Flask application code.
* Runs the server with: `pipenv run python app.py`

**Production deployment uses:**
```
web_app/docker-compose.prod.yml
```

This file:
* Pulls the web application image (`danielleesignup/web_app:latest`).
* Sets `FLASK_ENV=production`.
* Sets `API_BASE_URL` to the production Search API endpoint.
* Exposes container port 5000 to host port 80.

## How Production Deployment Works on the Server

On the production host (e.g., a DigitalOcean droplet), the structure is typically:

```
/opt/project_5/api
/opt/project_5/web_app
```

Each directory contains the corresponding `docker-compose.prod.yml` file.

**To deploy or restart:**

```bash
cd /opt/project_5/api
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

cd /opt/project_5/web_app
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

This updates all services, restarts them, and applies the latest images.

**Services run as:**
* `web_app` → port 80
* `search_api` → port 8001
* `clob_display` → port 8002
* `ws_clob` → port 8003
* `redis` → port 6379

## Production Notes

1. All environment variables are loaded from:
   ```
   /opt/project_5/.env
   ```

2. GitHub Actions is configured to automatically:
   * Build images
   * Push to Docker Hub
   * SSH into the server
   * Run `docker-compose pull` and `up -d` commands

3. The production server must have:
   * Docker installed
   * docker-compose installed
   * A firewall that allows ports 80, 8001, 8002, 8003

   # SECTION 9 — TESTING

This section explains how to run tests for both the web application and the API microservices, as well as where tests are located and how they are structured.

## Testing Overview

Poly Paper includes two independent test suites:

1. Tests for the Flask web application — located in `web_app/tests/`
2. Tests for the API microservices — located in `api/tests/`

Both use `pytest` as the testing framework, with optional plugins such as `pytest-asyncio` for async API tests.

## Pytest Configuration

At the root of the repository, `pyproject.toml` contains shared pytest settings, including:

* Minimum pytest version
* Additional default CLI options
* Test discovery paths
* Python path configuration

This ensures consistency when running tests from any directory.

## Running Web Application Tests

Navigate to the web_app directory:

```bash
cd web_app
```

Install development dependencies (if you have not already):

```bash
pipenv install --dev
```

Run the test suite:

```bash
pipenv run pytest
```

Tests in this directory typically cover:
* Routing behavior
* Template rendering
* Login and registration logic
* Settings update functionality

## Running API Tests

Navigate to the api directory:

```bash
cd api
```

Install development dependencies (if you are not using Docker for testing):

```bash
pipenv install --dev
```

Run the full API test suite:

```bash
pipenv run pytest
```

These tests cover:
* Search API response handling
* Redis caching behavior
* CLOB API responses and error cases
* WebSocket behavior (where implemented)

## Testing With Docker (Optional)

If you want tests to run inside a consistent container environment, you may manually enter a container or define separate Docker testing images.

**Typical manual approach:**

1. Start API services plus Redis:
   ```bash
   docker compose up --build
   ```

2. Run tests locally after services start:
   ```bash
   pipenv run pytest
   ```

For full CI automation, GitHub Actions already executes:
* pytest for the web app
* pytest for the API layer
* Coverage checks
* Formatting checks
* Linting

## Troubleshooting Failed Tests

Common issues include:

* Missing `.env` variables
* Redis not running when API tests expect caching
* MongoDB not reachable for web_app tests involving login/registration
* Old dependencies cached in Pipenv
* `API_BASE_URL` not set correctly in the test environment

**To reset Pipenv environment:**

```bash
pipenv --rm
pipenv install --dev
```

# SECTION 10 — CI/CD PIPELINE

This section describes how automated testing, image building, and deployment are handled through GitHub Actions. The project uses two separate pipelines: one for the web application and one for the API layer.

## Overview of CI/CD

GitHub Actions runs workflows whenever code is pushed or a pull request is opened. On pushes to the main branch, both pipelines also build Docker images and deploy to the production server.

**Workflows are stored in:**
```
.github/workflows/
```

There are two primary workflow files:
* `web-app-ci.yml`
* `api-ci.yml`

Each workflow performs:
1. Linting
2. Code formatting checks
3. Running the test suite
4. Building a Docker image
5. Pushing the image to Docker Hub
6. SSHing into the production server
7. Running `docker-compose pull` + `up -d` to redeploy
8. Performing a health check

## Web App CI/CD (web-app-ci.yml)

**Triggered by:**
* Push to main
* Pull requests targeting main

**Pipeline steps:**
1. Set up Python and install dependencies with Pipenv
2. Lint using pylint
3. Check formatting using black
4. Run pytest with coverage requirements
5. Build Docker image for the Flask web app
6. Push image to Docker Hub (`danielleesignup/web_app:latest`)
7. SSH into the production server
8. Navigate to `/opt/project_5/web_app`
9. Run:
   ```bash
   docker compose -f docker-compose.prod.yml pull
   docker compose -f docker-compose.prod.yml up -d
   ```
10. Health check on port 80 of the server

## API CI/CD (api-ci.yml)

Triggered similarly to the web app workflow.

**Pipeline steps:**
1. Set up Python
2. Install dependencies
3. Lint and format checks
4. Run pytest (includes async tests)
5. Build three images:
   * `api-search_api:latest`
   * `api-clob_display:latest`
   * `api-ws_clob:latest`
6. Push all images to Docker Hub
7. SSH into the production server
8. Navigate to `/opt/project_5/api`
9. Run:
   ```bash
   docker compose -f docker-compose.prod.yml pull
   docker compose -f docker-compose.prod.yml up -d
   ```
10. Health check for the Search API on port 8001

## Deployment Requirements

To make CI/CD work correctly, the production server must have:

* Docker installed
* docker-compose installed
* SSH access configured using GitHub Actions secrets
* Project files located at:
  ```
  /opt/project_5/api
  /opt/project_5/web_app
  ```

Environment variables for the server must be in:
```
/opt/project_5/.env
```

**Docker Hub credentials must be stored as GitHub secrets:**
* `DOCKERHUB_USERNAME`
* `DOCKERHUB_TOKEN`

**SSH credentials must also be stored:**
* `SSH_HOST`
* `SSH_USER`
* `SSH_PRIVATE_KEY`

## Health Check Behavior

Each workflow ends with a curl request to verify service health:

* **Web App:** `curl http://<server>:80/`
* **API:** `curl http://<server>:8001/health`

If the health check fails, the deployment step returns an error.

# SECTION 11 — LIMITATIONS AND FUTURE WORK

This section outlines the current boundaries of the Poly Paper system and identifies areas where functionality will be expanded in future iterations.

## Current Limitations

### 1. Market Data in the Web App Is Mocked
* The markets list and market detail pages do not yet pull data from the Search API or CLOB API.
* Prices, volumes, and questions shown in the UI are placeholders.

### 2. Portfolio Data Is Also Mocked
* The user portfolio page is hardcoded with example positions.
* No trade history, PnL, or position tracking is implemented yet.

### 3. No Paper Trading Logic Implemented
* Users cannot place trades.
* No order matching, fills, or validations occur.
* No record of hypothetical PnL or portfolio value changes.

### 4. WebSocket Data Not Integrated into the UI
* The WebSocket CLOB API runs successfully but does not feed into the front-end yet.
* Real-time streaming charts or price tickers are not implemented.

### 5. No Group Functionality
* Although a `group_id` field exists in user documents, all users currently default to group 0.
* No group portfolio or leaderboard logic exists.

### 6. Limited Error Handling in the Web App
* The Flask layer currently assumes API availability.
* Failover behavior for API outages is not implemented.

### 7. CI/CD Deploys Only "Latest" Images
* No environment tagging or version tracking.
* Rollbacks require manual intervention.

## Future Work

### 1. Full Integration of Market Data
* Web app routes will query:
  * **Search API** → for market discovery
  * **CLOB API** → for prices
* Replace all mock market data with API responses.

### 2. Implement Paper Trading Engine
* Store user trades and positions in MongoDB.
* Add order placement, buy/sell UI, and trade validation.
* Compute PnL based on CLOB mid-prices or simulated fills.

### 3. Add Real-Time UI Components
* Integrate `ws_clob` WebSocket stream into the front-end.
* Display live price updates, volatility indicators, or bid/ask ladders.

### 4. Build Group Functionality
* Teams, leaderboards, and competitive trading.
* Group-based performance ranking.

### 5. Improve Front-End Design
* Replace basic templates with responsive layouts.
* Add charts, graphs, and historical performance.

### 6. Introduce API Authentication (Optional)
* JWT or session-based tokens for protected endpoints.
* Rate limiting for abuse prevention.

### 7. Robust Deployment Strategy
* Add versioned Docker tags (e.g., `v1`, `v1.1`).
* Improve rollback strategy.
* Add staging environment deployment workflow.

### 8. Expanded Testing
* UI integration tests.
* More extensive async tests for API and WebSocket services.
* Load tests for Redis caching and Polymarket endpoint rate limits.

## Summary

Poly Paper provides a working foundation: a full-stack architecture, authentication, a multi-service API layer, caching, CI/CD, and deployable Docker environments. The next development phases will focus on replacing mock data with real Polymarket data, adding paper-trading mechanics, and integrating real-time streams to deliver an accurate trading simulation experience.

# SECTION 12 — ACKNOWLEDGEMENTS AND TEAM

## Purpose

This section recognizes contributors and external technologies that made Poly Paper possible. It is optional in formal documentation but useful for academic or team-based submissions.

## Project Contributors

Poly Paper was developed collaboratively as part of a team project.

**-Daniel Lee (@danielleesignup)**

Roles typically included:

### Backend Development
* Implementation of FastAPI microservices
* Redis caching integration
* CLOB and Polymarket API connectivity

### Web Application Development
* Flask routing, login system, and page logic
* MongoDB integration
* Front-end templates and UX structure

### Infrastructure and Deployment
* Dockerfile creation and containerization
* docker-compose for local and production environments
* CI/CD pipelines using GitHub Actions
* Server deployment, environment variable management, and health checks

### Testing and QA
* pytest suites for the API and web_app
* Continuous integration checks (linting, formatting, coverage)
* Production deployment verifications

## External Services and Libraries

Poly Paper relies on the following key technologies:

* **Flask** — Web application framework for routing and templates
* **FastAPI** — Modern async framework for the API microservices
* **Redis** — Caching backend for API results
* **MongoDB** — Storage for user accounts and metadata
* **py_clob_client** — Library used to interact with Polymarket's CLOB
* **Pipenv** — Dependency management for the Flask application
* **Docker & Docker Compose** — Containerization and orchestration
* **GitHub Actions** — Continuous integration and deployment automation

## Special Thanks

* The Polymarket engineering documentation, which informed API and CLOB integration.
* Open-source maintainers of FastAPI, Flask, and Redis clients.
* Team mentors and reviewers who provided feedback during development.

## Closing Note

Poly Paper establishes a flexible foundation for building a realistic prediction-market simulator. The project architecture is intentionally modular to support feature growth, real-time data integration, and scalable deployment strategies.

An exercise to put to practice software development teamwork, subsystem communication, containers, deployment, and CI/CD pipelines. See [instructions](./instructions.md) for details.

