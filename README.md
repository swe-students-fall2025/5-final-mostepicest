[![Web App CI](https://github.com/swe-students-fall2025/5-final-mostepicest/actions/workflows/web-app-ci.yml/badge.svg?branch=main)](https://github.com/swe-students-fall2025/5-final-mostepicest/actions/workflows/web-app-ci.yml)
[![API CI](https://github.com/swe-students-fall2025/5-final-mostepicest/actions/workflows/api-ci.yml/badge.svg?branch=main)](https://github.com/swe-students-fall2025/5-final-mostepicest/actions/workflows/api-ci.yml)

# Poly Paper

A Full-Stack Paper Trading Simulation Platform  
MostEpicest — Final Project (SWE)

## Overview 

PolyPaper is a paper-trading web application that lets users practice trading on event-based markets (similar to Polymarket) using real-time market data. Users can create an account, explore active event markets, and make trades with virtual funds. The users activity is tracked in a personal portfolio that updates with real-time returns, helping users learn how prediction markets work without risking real money.

Live Demo: http://64.225.22.79/

# FEATURES

## Web Application ('web_app/')
* User registration, login, logout.
* Password hashing with bcrypt.
* Session handling with Flask-Login.
* User data stored in MongoDB.
* Included pages:
  * `/register`
  * `/login`
  * `/portfolio` (mock data)
  * `/markets` and `/markets/<id>` (mock data)
  * `/settings` (username and balance update)

# INSTALLATION AND SETUP

## 1. Prerequisites

Before running the project locally, install the following:

* Python 3.10+ (for web_app) and Python 3.11+ (for API services)
* Pipenv (for managing the Flask app environment)
* Docker and Docker Compose (for the API microservices and Redis)
* A local or cloud-hosted MongoDB instance

If MongoDB is not installed locally, you may use MongoDB Atlas and update your `.env` accordingly.

**Example `.env`:**
```
MONGO_URI=mongodb://localhost:27017/polypaper
SECRET_KEY=dev-secret-key-change-me
SEARCH_URL=http://localhost:8001
PRICE_SERVICE_URL=http://localhost:8002
```

## 2. Run the Web Application (Flask)

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

### API Layer (api/)

The project contains two FastAPI microservices, each running in its own container.

1. **Search API – `search_api.py`**  
   - Proxies Polymarket’s search endpoint  
   - Caches responses in Redis  
   - Example: `http://localhost:8001/search?q=btc&page=1`


2. **Price API – `price_api.py`**  
   - Provides current CLOB prices and historical price data  
   - Includes retry logic + Redis caching  
   - Examples:  
     - `http://localhost:8002/clob?tokens=123,456`  
     - `http://localhost:8002/historical_prices?assets=123&assets=456&interval=1h`

## Run all API services:

Navigate to the API directory:

```bash
cd api
```

Start all API services (Search API, Price API) along with Redis:

```bash
docker compose up --build
```

Services will start at:
* Search API → `http://localhost:8001`
* Price API → `http://localhost:8002`
* Redis → `localhost:6379`

## Quick Tests

### Verify Search API:

```bash
curl "http://localhost:8001/search?q=btc&page=1"
```

### Verify Price API (CLOB endpoint):

```bash
curl "http://localhost:8002/clob?tokens=123"
```

If both commands return structured JSON, the API layer is functioning correctly.

## Environment Variables

At the root directory, create a `.env` file if one does not exist.

**Example `.env`:**
```
MONGO_URI=mongodb://localhost:27017/polypaper
SECRET_KEY=dev-secret-key-change-me
API_BASE_URL=http://localhost:8001
```

API services rely on:
```
REDIS_HOST=redis
REDIS_PORT=6379
```

**Note:**
* Use a secure secret key for production.
* API_BASE_URL refers to the Search API endpoint during development.

# TESTING

## Web App Tests

```bash
cd web_app
pipenv install --dev
pipenv run pytest
```

Tests in this directory typically cover:
* Routing behavior
* Template rendering
* Login and registration logic
* Settings update functionality

## API Tests

Navigate to the api directory:

```bash
cd api
pipenv install --dev
pipenv run pytest
```

These tests cover:
* Search API response handling
* Redis caching behavior
* Price API responses and error cases

## Production Deployment (Summary)

Poly Paper is deployed using **Docker Compose** + **GitHub Actions**.

Each subsystem (`web_app` and `api`) has its own `docker-compose.prod.yml` file.

### CI/CD Pipeline Overview
- Runs tests and formatting checks  
- Builds Docker images  
- Pushes images to Docker Hub  
- SSHes into the production server  
- Restarts services using:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

- **Production Services**
   - Flask Web App → port 80
   - Search API → port 8001
   - Price API → port 8002
   - Redis → port 6379

Environment variables for production are loaded from the server's .env file.

## Architecture Summary

The system is composed of two major components:

- **Web Application (`web_app/`)** — A Flask-based interface that manages users, sessions, authentication, and the UI.
- **API Layer (`api/`)** — Two FastAPI microservices that provide market search and CLOB price retrieval (with historical pricing), backed by Redis caching.

Poly Paper is designed as a modular system: the UI interacts with separate, containerized services that proxy and cache Polymarket data. This separation enables flexible scaling, clearer responsibility boundaries, and an easier path for full paper-trade simulation.

### Overview of Components
- **Flask Web App (`web_app/`)**
  - Manages sign-up, login, logout, and settings
  - Serves HTML templates for markets, portfolio, and settings
  - Talks to MongoDB for user data
  - Will use the API layer for real Polymarket data in future iterations

- **Fast API Microservices**
  - Proxy Polymarket APIs
  - Redis caching for performance

- **Supporting Infrastructure**
   - **MongoDB** — stores user accounts, hashed passwords, and metadata  
   - **Redis** — shared caching backend for all API services  
   - **Docker / Docker Compose** — containerization for the API layer and production deployment
   - **Github Actions for CI/CD**

**Data Flow (high-level)**

1. User interacts with Flask UI.
2. Flask handles auth + UI rendering.
3. When market data is needed, the frontend (eventually) will call the API microservices over HTTP.
4. APIs services fetch live data from Polymarket or return cached results from Redis.
5. The data flows back to the frontend to render market/price information.

---

## Project Contributors

Poly Paper was developed collaboratively as part of a team project.

**-[Daniel Lee](https://github.com/dl4458-lgtm)**

**-[Amira Adum](https://github.com/amiraadum)**

**-[Kevin Pham](https://github.com/knp4830)**

**-[Jasir Nawar](https://github.com/jawarbx)**

**-[Omer Hortig](https://github.com/ohortig)**

---
