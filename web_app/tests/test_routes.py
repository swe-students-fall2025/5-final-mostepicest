"""
Web_app route tests.
"""

from unittest.mock import patch, MagicMock


# =============================================================================
# HOME ROUTE TESTS
# =============================================================================


class TestHomeRoute:
    """Tests for the home route (/)."""

    def test_home_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated user should be redirected to login."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code in (301, 302)
        assert "/login" in response.location

    def test_home_authenticated_redirects_to_portfolio(self, auth_client):
        """Authenticated user should be redirected to portfolio."""
        response = auth_client.get("/", follow_redirects=False)
        assert response.status_code in (301, 302)
        assert "/portfolio" in response.location


# =============================================================================
# REGISTRATION TESTS
# =============================================================================


class TestRegistration:
    """Tests for the registration route (/register)."""

    def test_register_get_renders_form(self, client):
        """GET /register should render the registration form."""
        response = client.get("/register")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Register" in html
        assert "Email" in html
        assert "Username" in html
        assert "Password" in html

    def test_register_success_creates_user_and_redirects(self, app, client):
        """POST /register with valid data should create user and redirect to portfolio."""
        mock_db = app._mock_db
        mock_db.users.find_one.return_value = None  # No existing user
        mock_db.users.insert_one.return_value = MagicMock()

        response = client.post(
            "/register",
            data={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "ValidPass1!",
                "confirm_password": "ValidPass1!",
            },
            follow_redirects=False,
        )

        assert response.status_code in (301, 302)
        assert "/portfolio" in response.location
        mock_db.users.insert_one.assert_called_once()

    def test_register_empty_email_shows_error(self, client):
        """POST /register with empty email should show error."""
        response = client.post(
            "/register",
            data={
                "email": "",
                "username": "testuser",
                "password": "ValidPass1!",
                "confirm_password": "ValidPass1!",
            },
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Email is required" in html

    def test_register_empty_username_shows_error(self, client):
        """POST /register with empty username should show error."""
        response = client.post(
            "/register",
            data={
                "email": "test@example.com",
                "username": "",
                "password": "ValidPass1!",
                "confirm_password": "ValidPass1!",
            },
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Username is required" in html

    def test_register_empty_password_shows_error(self, client):
        """POST /register with empty password should show error."""
        response = client.post(
            "/register",
            data={
                "email": "test@example.com",
                "username": "testuser",
                "password": "",
                "confirm_password": "",
            },
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Password is required" in html

    def test_register_password_mismatch_shows_error(self, client):
        """POST /register with mismatched passwords should show error."""
        response = client.post(
            "/register",
            data={
                "email": "test@example.com",
                "username": "testuser",
                "password": "ValidPass1!",
                "confirm_password": "DifferentPass1!",
            },
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Passwords do not match" in html

    def test_register_existing_email_shows_error(self, app, client):
        """POST /register with existing email should show error."""
        mock_db = app._mock_db
        mock_db.users.find_one.return_value = {"email": "existing@example.com"}

        response = client.post(
            "/register",
            data={
                "email": "existing@example.com",
                "username": "newuser",
                "password": "ValidPass1!",
                "confirm_password": "ValidPass1!",
            },
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Email is already registered" in html

    def test_register_existing_username_shows_error(self, app, client):
        """POST /register with existing username should show error."""
        mock_db = app._mock_db

        # First call (email check) returns None, second call (username check) returns user
        mock_db.users.find_one.side_effect = [None, {"username": "existinguser"}]

        response = client.post(
            "/register",
            data={
                "email": "new@example.com",
                "username": "existinguser",
                "password": "ValidPass1!",
                "confirm_password": "ValidPass1!",
            },
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Username is already taken" in html

    def test_register_password_too_short_shows_error(self, app, client):
        """POST /register with password < 8 chars should show error."""
        mock_db = app._mock_db
        mock_db.users.find_one.return_value = None

        response = client.post(
            "/register",
            data={
                "email": "test@example.com",
                "username": "testuser",
                "password": "Short1!",
                "confirm_password": "Short1!",
            },
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Password must be at least 8 characters long" in html

    def test_register_password_no_uppercase_shows_error(self, app, client):
        """POST /register with password missing uppercase should show error."""
        mock_db = app._mock_db
        mock_db.users.find_one.return_value = None

        response = client.post(
            "/register",
            data={
                "email": "test@example.com",
                "username": "testuser",
                "password": "lowercase1!",
                "confirm_password": "lowercase1!",
            },
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Password must contain at least one uppercase letter" in html

    def test_register_password_no_lowercase_shows_error(self, app, client):
        """POST /register with password missing lowercase should show error."""
        mock_db = app._mock_db
        mock_db.users.find_one.return_value = None

        response = client.post(
            "/register",
            data={
                "email": "test@example.com",
                "username": "testuser",
                "password": "UPPERCASE1!",
                "confirm_password": "UPPERCASE1!",
            },
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Password must contain at least one lowercase letter" in html

    def test_register_password_no_number_shows_error(self, app, client):
        """POST /register with password missing number should show error."""
        mock_db = app._mock_db
        mock_db.users.find_one.return_value = None

        response = client.post(
            "/register",
            data={
                "email": "test@example.com",
                "username": "testuser",
                "password": "NoNumber!!",
                "confirm_password": "NoNumber!!",
            },
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Password must contain at least one number" in html

    def test_register_password_no_special_char_shows_error(self, app, client):
        """POST /register with password missing special char should show error."""
        mock_db = app._mock_db
        mock_db.users.find_one.return_value = None

        response = client.post(
            "/register",
            data={
                "email": "test@example.com",
                "username": "testuser",
                "password": "NoSpecial1",
                "confirm_password": "NoSpecial1",
            },
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Password must contain at least one special character" in html

    def test_register_database_error_shows_error(self, app, client):
        """POST /register with database error should show error."""
        mock_db = app._mock_db
        mock_db.users.find_one.return_value = None
        mock_db.users.insert_one.side_effect = Exception("Database connection failed")

        response = client.post(
            "/register",
            data={
                "email": "test@example.com",
                "username": "testuser",
                "password": "ValidPass1!",
                "confirm_password": "ValidPass1!",
            },
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Error creating account" in html


# =============================================================================
# LOGIN TESTS
# =============================================================================


class TestLogin:
    """Tests for the login route (/login)."""

    def test_login_get_renders_form(self, client):
        """GET /login should render the login form."""
        response = client.get("/login")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Login" in html
        assert "Email" in html
        assert "Password" in html

    def test_login_valid_credentials_redirects_to_portfolio(self, app, client, bcrypt):
        """POST /login with valid credentials should redirect to portfolio."""
        mock_db = app._mock_db
        hashed_password = bcrypt.generate_password_hash("ValidPass1!").decode("utf-8")

        mock_db.users.find_one.return_value = {
            "user_id": "test-user-id",
            "email": "test@example.com",
            "username": "testuser",
            "password": hashed_password,
            "group_id": 0,
        }

        response = client.post(
            "/login",
            data={"email": "test@example.com", "password": "ValidPass1!"},
            follow_redirects=False,
        )

        assert response.status_code in (301, 302)
        assert "/portfolio" in response.location

    def test_login_invalid_email_shows_error(self, app, client):
        """POST /login with non-existent email should show error."""
        mock_db = app._mock_db
        mock_db.users.find_one.return_value = None

        response = client.post(
            "/login",
            data={"email": "nonexistent@example.com", "password": "SomePassword1!"},
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Invalid email or password" in html

    def test_login_wrong_password_shows_error(self, app, client, bcrypt):
        """POST /login with wrong password should show error."""
        mock_db = app._mock_db
        hashed_password = bcrypt.generate_password_hash("CorrectPass1!").decode("utf-8")

        mock_db.users.find_one.return_value = {
            "user_id": "test-user-id",
            "email": "test@example.com",
            "username": "testuser",
            "password": hashed_password,
            "group_id": 0,
        }

        response = client.post(
            "/login", data={"email": "test@example.com", "password": "WrongPassword1!"}
        )
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Invalid email or password" in html


# =============================================================================
# LOGOUT TESTS
# =============================================================================


class TestLogout:
    """Tests for the logout route (/logout)."""

    def test_logout_authenticated_user_redirects_to_login(self, auth_client):
        """Authenticated user logging out should redirect to login."""
        response = auth_client.get("/logout", follow_redirects=False)
        assert response.status_code in (301, 302)
        assert "/login" in response.location

    def test_logout_unauthenticated_user_redirects(self, client):
        """Unauthenticated user accessing logout should be redirected."""
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code in (301, 302)
        assert "/login" in response.location


# =============================================================================
# PORTFOLIO TESTS
# =============================================================================


class TestPortfolio:
    """Tests for the portfolio route (/portfolio)."""

    def test_portfolio_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated user should be redirected to login."""
        response = client.get("/portfolio", follow_redirects=False)
        assert response.status_code in (301, 302)
        assert "/login" in response.location

    def test_portfolio_authenticated_shows_content(self, auth_client):
        """Authenticated user should see portfolio content."""
        response = auth_client.get("/portfolio")
        assert response.status_code == 200
        html = response.data.decode("utf-8")

        # From base.html
        assert "PolyPaper" in html

        # Portfolio page content
        assert "Portfolio" in html

    def test_portfolio_shows_positions(self, auth_client):
        """Portfolio page should display positions."""
        response = auth_client.get("/portfolio")
        assert response.status_code == 200

    def test_portfolio_shows_user_balance(self, auth_client):
        """Portfolio page should display user balance."""
        response = auth_client.get("/portfolio")
        assert response.status_code == 200

    def test_portfolio_nav_links_present(self, auth_client):
        """Portfolio page should have navigation links."""
        response = auth_client.get("/portfolio")
        assert response.status_code == 200
        html = response.data.decode("utf-8")

        assert "Portfolio" in html
        assert "Markets" in html
        assert "Watchlist" in html


# =============================================================================
# MARKETS TESTS
# =============================================================================


class TestMarkets:
    """Tests for the markets route (/markets)."""

    def test_markets_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated user should be redirected to login."""
        response = client.get("/markets", follow_redirects=False)
        assert response.status_code in (301, 302)
        assert "/login" in response.location

    def test_markets_authenticated_shows_all_markets(self, auth_client):
        """Authenticated user should see all markets."""
        response = auth_client.get("/markets")
        assert response.status_code == 200

    def test_markets_search_filters_by_question(self, auth_client):
        """Search should filter markets by question text."""
        response = auth_client.get("/markets?q=btc")
        assert response.status_code == 200

    def test_markets_search_filters_by_region(self, auth_client):
        """Search should filter markets by region."""
        response = auth_client.get("/markets?q=usa")
        assert response.status_code == 200

    def test_markets_search_filters_by_category(self, auth_client):
        """Search should filter markets by category."""
        response = auth_client.get("/markets?q=crypto")
        assert response.status_code == 200

    def test_markets_search_no_results(self, auth_client):
        """Search with no matches should show empty results."""
        response = auth_client.get("/markets?q=nonexistent")
        assert response.status_code == 200

    def test_markets_page_title(self, auth_client):
        """Markets page should have proper title and subtitle."""
        response = auth_client.get("/markets")
        assert response.status_code == 200
        html = response.data.decode("utf-8")

        assert "Markets" in html


# =============================================================================
# MARKET DETAIL TESTS
# =============================================================================


class TestMarketDetail:
    """Tests for the market detail route (/markets/<id>)."""

    def test_market_detail_unauthenticated_redirects(self, client):
        """Unauthenticated user should be redirected to login."""
        response = client.get("/markets/1", follow_redirects=False)
        assert response.status_code in (301, 302)
        assert "/login" in response.location

    def test_market_detail_valid_id_shows_content(self, auth_client):
        """Valid market ID should show market details."""
        response = auth_client.get("/markets/1")
        assert response.status_code == 200

    def test_market_detail_all_markets_accessible(self, auth_client):
        """All valid market IDs should be accessible."""
        for market_id in [1, 2, 3]:
            response = auth_client.get(f"/markets/{market_id}")
            assert response.status_code == 200

    def test_market_detail_invalid_id_returns_404(self, auth_client):
        """Invalid market ID should return 404."""
        response = auth_client.get("/markets/999")
        assert response.status_code == 404

    def test_market_detail_shows_trade_ticket(self, auth_client):
        """Market detail page should show trade ticket."""
        response = auth_client.get("/markets/1")
        assert response.status_code == 200
        html = response.data.decode("utf-8")

        assert "Place a paper trade" in html


# =============================================================================
# USER LOADER TESTS
# =============================================================================


class TestUserLoader:
    """Tests for the user_loader function."""

    def test_user_loader_returns_user_when_found(self, app):
        """user_loader should return User when user exists."""
        from web_app.app import load_user

        mock_db = app._mock_db
        mock_db.users.find_one.return_value = {
            "user_id": "test-user-id",
            "email": "test@example.com",
            "username": "testuser",
            "group_id": 0,
        }

        with app.app_context():
            user = load_user("test-user-id")
            assert user is not None
            assert user.id == "test-user-id"
            assert user.email == "test@example.com"
            assert user.username == "testuser"

    def test_user_loader_returns_none_when_not_found(self, app):
        """user_loader should return None when user doesn't exist."""
        from web_app.app import load_user

        mock_db = app._mock_db
        mock_db.users.find_one.return_value = None

        with app.app_context():
            user = load_user("nonexistent-user-id")
            assert user is None

    def test_user_loader_returns_none_on_exception(self, app):
        """user_loader should return None when exception occurs."""
        from web_app.app import load_user

        mock_db = app._mock_db
        mock_db.users.find_one.side_effect = Exception("Database error")

        with app.app_context():
            user = load_user("test-user-id")
            assert user is None


# =============================================================================
# USER CLASS TESTS
# =============================================================================


class TestUserClass:
    """Tests for the User class."""

    def test_user_creation(self, app):
        """User class should properly initialize with given data."""
        from web_app.app import User

        user = User(
            user_id="test-id", email="test@example.com", username="testuser", group_id=1
        )

        assert user.id == "test-id"
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.group_id == 1

    def test_user_inherits_usermixin(self, app):
        """User class should inherit from UserMixin."""
        from web_app.app import User
        import flask_login

        user = User(
            user_id="test-id", email="test@example.com", username="testuser", group_id=1
        )

        assert hasattr(user, "is_authenticated")
        assert hasattr(user, "is_active")
        assert hasattr(user, "is_anonymous")
        assert hasattr(user, "get_id")
        assert user.is_authenticated is True
        assert user.is_active is True
        assert user.is_anonymous is False
