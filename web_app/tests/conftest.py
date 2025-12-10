"""
Pytest configuration and shared fixtures for web_app tests.
"""

from unittest.mock import MagicMock, patch

import pytest
from flask_bcrypt import Bcrypt


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "user_id": "test-user-id-12345",
        "email": "test@example.com",
        "username": "testuser",
        "password": "hashed_password_placeholder",
        "group_id": 0,
        "portfolio_id": "test-portfolio-id-12345",
        "created_at": "2025-01-01T00:00:00Z",
        "deleted_at": None,
    }


@pytest.fixture
def mock_db():
    """Create a mock MongoDB database."""
    mock = MagicMock()
    mock.users = MagicMock()
    mock.users.find_one = MagicMock(return_value=None)
    mock.users.insert_one = MagicMock()
    return mock


@pytest.fixture
def app(mock_db):
    """Create Flask app with test configuration."""
    # Patch MongoClient before importing/reloading
    with patch("pymongo.MongoClient") as mock_client:
        # Configure mock to return our mock_db when accessed with ["polypaper"]
        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client.return_value = mock_client_instance

        import web_app.app as app_module

        # Patch db directly to ensure all references use mock
        with patch.object(app_module, "db", mock_db):
            flask_app = app_module.app
            flask_app.config["TESTING"] = True
            flask_app.config["SECRET_KEY"] = "test-secret-key"

            # Configure Flask-Login to redirect to login page instead of returning 401
            app_module.login_manager.login_view = "login"

            # Store mock_db reference on app for tests to access
            flask_app._mock_db = mock_db

            yield flask_app


@pytest.fixture
def client(app):
    """Create unauthenticated test client."""
    return app.test_client()


@pytest.fixture
def auth_client(app, mock_db, sample_user_data):
    """Create authenticated test client with logged-in user."""
    # Set up user data for user_loader
    user_data = sample_user_data.copy()

    # Configure mock to return user for user_loader (when load_user is called)
    mock_db.users.find_one.return_value = user_data

    client = app.test_client()

    # Set up Flask-Login session directly
    with client.session_transaction() as sess:
        # Flask-Login stores user_id in session under '_user_id'
        sess["_user_id"] = user_data["user_id"]
        sess["_fresh"] = True

    yield client


@pytest.fixture
def bcrypt(app):
    """Bcrypt instance for password hashing in tests."""
    return Bcrypt(app)
