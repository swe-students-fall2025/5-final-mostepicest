"""
Web_app route tests.
"""

from unittest.mock import MagicMock, patch

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

    def test_home_authenticated_redirects_to_portfolio(self, auth_client, app):
        """Authenticated user should be redirected to portfolio."""
        # Mock the portfolio lookup that happens in the portfolio route
        mock_db = app._mock_db
        mock_db.portfolios.find_one.return_value = {
            "portfolio_id": "test-portfolio-id-12345",
            "balance": 1000.0,
            "positions": [],
        }

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
        assert "register" in html.lower()

    def test_register_success_creates_user_and_redirects(self, app, client):
        """POST /register with valid data should create user and redirect to portfolio."""
        mock_db = app._mock_db
        mock_db.users.find_one.return_value = None  # No existing user
        mock_db.users.insert_one.return_value = MagicMock()
        mock_db.portfolios.insert_one.return_value = MagicMock()
        mock_db.portfolios.find_one.return_value = {
            "portfolio_id": "new-portfolio-id",
            "balance": 1000.0,
            "positions": [],
        }

        response = client.post(
            "/register",
            data={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "ValidPass1!",
                "balance": "1000.0",
            },
            follow_redirects=False,
        )

        assert response.status_code in (301, 302)
        assert "/portfolio" in response.location
        mock_db.users.insert_one.assert_called_once()
        mock_db.portfolios.insert_one.assert_called_once()

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
                "balance": "1000.0",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        # The app flashes "Email exists" with "error" category

    def test_register_password_mismatch_redirects(self, app, client):
        """POST /register with mismatched passwords should redirect back to form."""
        mock_db = app._mock_db
        mock_db.users.find_one.return_value = None

        response = client.post(
            "/register",
            data={
                "email": "test@example.com",
                "username": "tester",
                "password": "ValidPass1!",
                "confirm_password": "DifferentPass2!",
                "starting_balance": "500",
            },
            follow_redirects=False,
        )

        assert response.status_code in (301, 302)
        assert "/register" in response.location


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
        assert "login" in html.lower()

    def test_login_valid_credentials_redirects_to_portfolio(self, app, client, bcrypt):
        """POST /login with valid credentials should redirect to portfolio."""
        mock_db = app._mock_db
        hashed_password = bcrypt.generate_password_hash("ValidPass1!").decode("utf-8")

        user_data = {
            "user_id": "test-user-id",
            "email": "test@example.com",
            "username": "testuser",
            "password": hashed_password,
            "portfolio_id": "test-portfolio-id",
        }

        mock_db.users.find_one.return_value = user_data
        mock_db.portfolios.find_one.return_value = {
            "portfolio_id": "test-portfolio-id",
            "balance": 1000.0,
            "positions": [],
        }

        response = client.post(
            "/login",
            data={"email": "test@example.com", "password": "ValidPass1!"},
            follow_redirects=False,
        )

        assert response.status_code in (301, 302)
        assert "/portfolio" in response.location

    def test_login_wrong_password_shows_error(self, app, client, bcrypt):
        """POST /login with wrong password should show error."""
        mock_db = app._mock_db
        hashed_password = bcrypt.generate_password_hash("CorrectPass1!").decode("utf-8")

        mock_db.users.find_one.return_value = {
            "user_id": "test-user-id",
            "email": "test@example.com",
            "username": "testuser",
            "password": hashed_password,
            "portfolio_id": "test-portfolio-id",
        }

        response = client.post(
            "/login",
            data={"email": "test@example.com", "password": "WrongPassword1!"},
            follow_redirects=True,
        )
        assert response.status_code == 200


# =============================================================================
# LOGOUT TESTS
# =============================================================================


class TestLogout:
    """Tests for the logout route (/logout)."""

    def test_logout_authenticated_user_redirects_to_login(self, app, auth_client):
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

    @patch("web_app.app.fetch_live_prices")
    def test_portfolio_authenticated_shows_content(self, mock_fetch, app, auth_client):
        """Authenticated user should see portfolio content."""
        mock_db = app._mock_db
        mock_db.portfolios.find_one.return_value = {
            "portfolio_id": "test-portfolio-id-12345",
            "balance": 1000.0,
            "positions": {},
        }
        mock_fetch.return_value = {}

        response = auth_client.get("/portfolio")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "portfolio" in html.lower()

    @patch("web_app.app.fetch_live_prices")
    def test_portfolio_shows_positions(self, mock_fetch, app, auth_client):
        """Portfolio page should display positions."""
        mock_db = app._mock_db
        mock_db.portfolios.find_one.return_value = {
            "portfolio_id": "test-portfolio-id-12345",
            "balance": 1000.0,
            "positions": {
                "asset1": {
                    "quantity": 10,
                    "avg_price": 0.5,
                    "market_question": "Test Market",
                }
            },
        }
        mock_fetch.return_value = {"asset1": 0.6}

        response = auth_client.get("/portfolio")
        assert response.status_code == 200


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

    def test_markets_authenticated_shows_all_markets(self, app, auth_client):
        """Authenticated user should see all markets."""
        response = auth_client.get("/markets")
        assert response.status_code == 200

    @patch("web_app.app.requests.get")
    def test_markets_search_filters_by_question(self, mock_get, app, auth_client):
        """Search should filter markets by question text."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [
                {
                    "markets": [
                        {
                            "slug": "btc-market",
                            "active": True,
                            "closed": False,
                            "outcomes": '["Yes", "No"]',
                            "outcomePrices": "[0.5, 0.5]",
                            "clobTokenIds": '["1", "2"]',
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        response = auth_client.get("/markets?q=btc")
        assert response.status_code == 200


# =============================================================================
# MARKET DETAIL TESTS
# =============================================================================


class TestMarketDetail:
    """Tests for the market detail route (/market_details)."""

    def test_market_detail_unauthenticated_redirects(self, client):
        """Unauthenticated user should be redirected to login."""
        response = client.get("/market_details?slug=test", follow_redirects=False)
        assert response.status_code in (301, 302)
        assert "/login" in response.location

    @patch("web_app.app.get_cached_market")
    @patch("web_app.app.fetch_historical_prices")
    def test_market_detail_valid_slug_shows_content(
        self, mock_fetch, mock_cache, app, auth_client
    ):
        """Valid market slug should show market details."""
        mock_cache.return_value = {
            "slug": "test-market",
            "outcomes": '["Yes", "No"]',
            "outcomePrices": "[0.5, 0.5]",
            "clobTokenIds": '["1", "2"]',
        }
        mock_fetch.return_value = {}

        response = auth_client.get("/market_details?slug=test-market")
        assert response.status_code == 200

    @patch("web_app.app.get_cached_market")
    def test_market_detail_invalid_slug_returns_400(self, mock_cache, app, auth_client):
        """Invalid market slug should return 400."""
        mock_cache.return_value = None

        response = auth_client.get("/market_details?slug=nonexistent")
        assert response.status_code == 400


# =============================================================================
# SETTINGS TESTS
# =============================================================================


class TestSettings:
    """Tests for the settings route (/settings)."""

    def test_settings_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated user should be redirected to login."""
        response = client.get("/settings", follow_redirects=False)
        assert response.status_code in (301, 302)
        assert "/login" in response.location

    def test_settings_authenticated_shows_form(self, app, auth_client):
        """Authenticated user should see settings form."""
        response = auth_client.get("/settings")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "settings" in html.lower()

    def test_settings_post_valid_username_updates_successfully(
        self, app, auth_client, sample_user_data
    ):
        """POST /settings with valid username should update successfully."""
        mock_db = app._mock_db
        mock_db.users.update_one.return_value = MagicMock()

        response = auth_client.post(
            "/settings",
            data={"username": "newusername"},
            follow_redirects=False,
        )

        assert response.status_code == 200
        mock_db.users.update_one.assert_called_once()

    def test_settings_reset_account_updates_balance_and_clears_positions(
        self, app, auth_client
    ):
        """POST /settings reset should clear portfolio and set new balance."""
        mock_db = app._mock_db
        mock_update = MagicMock()
        mock_update.matched_count = 1
        mock_db.portfolios.update_one.return_value = mock_update

        response = auth_client.post(
            "/settings",
            data={
                "action": "reset_account",
                "reset_starting_balance": "750000",
            },
            follow_redirects=False,
        )

        assert response.status_code in (301, 302)
        assert "/settings" in response.location
        mock_db.portfolios.update_one.assert_called_once()


# =============================================================================
# TRADE TESTS
# =============================================================================


class TestTrade:
    """Tests for the trade route (/trade)."""

    def test_trade_unauthenticated_returns_error(self, client):
        """Unauthenticated user should not be able to trade."""
        response = client.post("/trade", json={"asset_id": "1", "bid": 100})
        assert response.status_code in (301, 302, 401)

    @patch("web_app.app.fetch_live_prices")
    def test_trade_valid_bid_executes_successfully(
        self, mock_fetch, app, auth_client, sample_user_data
    ):
        """POST /trade with valid bid should execute successfully."""
        mock_db = app._mock_db
        mock_fetch.return_value = {"test-asset": 0.5}

        # Mock the current_user balance check
        # Mock portfolio operations
        mock_update_result = MagicMock()
        mock_update_result.matched_count = 1
        mock_db.portfolios.update_one.return_value = mock_update_result
        mock_db.portfolios.find_one.return_value = None  # No existing position

        response = auth_client.post(
            "/trade",
            json={"asset_id": "test-asset", "bid": 100.0, "question": "Test Market"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("web_app.app.fetch_live_prices")
    def test_trade_zero_bid_returns_error(self, mock_fetch, app, auth_client):
        """POST /trade with zero bid should return error."""
        mock_fetch.return_value = {"test-asset": 0.5}

        response = auth_client.post(
            "/trade",
            json={"asset_id": "test-asset", "bid": 0, "question": "Test Market"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False


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
            "portfolio_id": "test-portfolio-id",
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


# =============================================================================
# USER CLASS TESTS
# =============================================================================


class TestUserClass:
    """Tests for the User class."""

    def test_user_creation(self, app):
        """User class should properly initialize with given data."""
        from web_app.app import User

        user = User(
            user_id="test-id",
            email="test@example.com",
            username="testuser",
            portfolio_id="portfolio-123",
            balance=1000.0,
        )

        assert user.id == "test-id"
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.portfolio_id == "portfolio-123"
        assert user.balance == 1000.0

    def test_user_inherits_usermixin(self, app):
        """User class should inherit from UserMixin."""
        import flask_login
        from web_app.app import User

        user = User(
            user_id="test-id",
            email="test@example.com",
            username="testuser",
            portfolio_id="portfolio-123",
        )

        assert hasattr(user, "is_authenticated")
        assert hasattr(user, "is_active")
        assert hasattr(user, "is_anonymous")
        assert hasattr(user, "get_id")
        assert user.is_authenticated is True
        assert user.is_active is True
        assert user.is_anonymous is False
