"Main app"

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List

import flask_login
import requests
from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_bcrypt import Bcrypt
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)
MARKET_CACHE = {}
CACHE_TTL = 300

app.secret_key = os.getenv("SECRET_KEY", "dev_secret")
PRICE_SERVICE_URL = os.getenv("PRICE_SERVICE_URL", "http://localhost:8002")
SEARCH_URL = os.getenv("SEARCH_URL", "http://localhost:8001")
MONGO_URI = os.getenv("MONGO_URI")

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client["polypaper"]
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    raise e


def cache_market(slug, market):
    MARKET_CACHE[slug] = {"market": market, "timestamp": time.time()}


def get_cached_market(slug):
    entry = MARKET_CACHE.get(slug)
    if not entry:
        return None
    # Check TTL
    if time.time() - entry["timestamp"] > CACHE_TTL:
        del MARKET_CACHE[slug]
        return None
    return entry["market"]


class User(flask_login.UserMixin):
    def __init__(self, user_id, email, username, portfolio_id, balance=0.0):
        self.id = user_id
        self.email = email
        self.username = username
        self.balance = balance
        self.portfolio_id = portfolio_id


@login_manager.user_loader
def load_user(user_id):
    u = db.users.find_one({"user_id": user_id})
    if not u:
        return None

    portfolio_id = u.get("portfolio_id")  # may be None for older users
    balance = u.get("balance", 0.0)  # Get balance from MongoDB, default to 0.0
    return User(u["user_id"], u["email"], u["username"], portfolio_id, balance)


# def load_user(user_id):
#     u = db.users.find_one({"user_id": user_id})
#     if u:
#         return User(u["user_id"], u["email"], u["username"], u["portfolio_id"])
#     return None


def fetch_live_prices(token_ids: List[str]) -> Dict[str, float]:
    """
    Fetch the latest prices for a list of asset IDs from the CLOB service.

    Args:
        token_ids (List[str]): List of asset IDs to fetch prices for.

    Returns:
        Dict[str, float]: Mapping of asset_id -> latest price. Empty dict if fetch fails.
    """
    if not token_ids:
        return {}

    # De-duplicate while preserving order to keep mapping stable
    seen = set()
    ordered_tokens = []
    for t in token_ids:
        if t in seen or t is None:
            continue
        seen.add(t)
        ordered_tokens.append(str(t))

    prices: Dict[str, float] = {}

    for token in ordered_tokens:
        try:
            params = {"tokens": token}
            resp = requests.get(f"{PRICE_SERVICE_URL}/clob", params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            # Normalize single-token response to a float
            price_val = None
            if isinstance(data, dict):
                # Try direct key, otherwise first value
                if token in data:
                    price_val = data[token]
                elif len(data.values()) > 0:
                    price_val = list(data.values())[0]
            elif isinstance(data, list) and len(data) > 0:
                price_val = data[0]

            if price_val is None:
                continue

            try:
                prices[str(token)] = float(price_val)
            except (TypeError, ValueError):
                continue
        except requests.RequestException as e:
            print(f"Price Fetch Error for token {token}: {e}")
            continue
        except Exception as e:
            print(f"Unexpected price parse error for token {token}: {e}")
            continue

    return prices


def fetch_historical_prices(asset_ids, interval="1h", fidelity=None):
    """Fetch historical prices for given asset IDs"""
    if not asset_ids:
        return {}
    try:
        # FastAPI List[str] Query accepts multiple query params
        # requests library automatically converts list to multiple query params
        params = {
            "assets": asset_ids,  # Pass as list, requests will format as ?assets=id1&assets=id2
            "interval": interval,
        }
        if fidelity is not None:
            params["fidelity"] = fidelity

        print(f"Fetching from: {PRICE_SERVICE_URL}/historical_prices")
        print(f"Params: {params}")

        resp = requests.get(
            f"{PRICE_SERVICE_URL}/historical_prices", params=params, timeout=30
        )
        print(f"Response status: {resp.status_code}")
        if resp.status_code == 200:
            return resp.json()
        print(f"Error response: {resp.text}")
    except requests.exceptions.ConnectionError as e:
        print(
            f"Connection Error - Is price_api running on {PRICE_SERVICE_URL}? Error: {e}"
        )
    except requests.exceptions.Timeout as e:
        print(f"Timeout Error: {e}")
    except Exception as e:
        print(f"Historical Price Fetch Error: {e}")
        import traceback

        traceback.print_exc()
    return {}


@app.context_processor
def inject_portfolio_data():
    """Make portfolio value and balance available to all templates"""
    if flask_login.current_user.is_authenticated:
        portfolio_id = flask_login.current_user.portfolio_id
        if portfolio_id:
            try:
                portfolio = db.portfolios.find_one({"portfolio_id": portfolio_id})
                if portfolio:
                    current_balance = portfolio.get("balance", 0.0)
                    positions = portfolio.get("positions", {})

                    # Calculate total portfolio value
                    total_value = 0
                    if positions:
                        asset_ids = list(positions.keys())
                        live_prices = fetch_live_prices(asset_ids)

                        for asset_id, info in positions.items():
                            # Use live price if available, else fallback to avg_price
                            current_price = float(
                                live_prices.get(asset_id, info.get("avg_price", 0.0))
                            )
                            market_val = current_price * info.get("quantity", 0.0)
                            total_value += market_val

                    return {
                        "header_portfolio_value": total_value,
                        "header_cash_balance": current_balance,
                    }
            except Exception as e:
                print(f"Error calculating portfolio data for header: {e}")

    # Default values if not authenticated or error occurs
    return {"header_portfolio_value": 0.0, "header_cash_balance": 0.0}


@app.route("/")
def home():
    if flask_login.current_user.is_authenticated:
        return redirect(url_for("portfolio"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password", password)
        # Support legacy field name "balance" used by some clients/tests
        starting_balance_raw = (
            request.form.get("starting_balance")
            or request.form.get("balance")
            or "1000000"
        )
        starting_balance_raw = str(starting_balance_raw).strip()

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        try:
            starting_balance = float(starting_balance_raw)
        except (TypeError, ValueError):
            flash("Starting balance must be between 1 and 1,000,000.", "error")
            return redirect(url_for("register"))

        if not 1 <= starting_balance <= 1_000_000:
            flash("Starting balance must be between 1 and 1,000,000.", "error")
            return redirect(url_for("register"))

        if db.users.find_one({"email": email}):
            flash("Email exists", "error")
            return redirect(url_for("register"))

        new_user = {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "username": username,
            "password": bcrypt.generate_password_hash(password).decode("utf-8"),
            "portfolio_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc),
        }
        db.users.insert_one(new_user)

        new_user_portfolio = {
            "portfolio_id": new_user["portfolio_id"],
            "balance": starting_balance,
            "created_at": new_user["created_at"],
            "positions": {},
            "transaction_history": {},
        }
        db.portfolios.insert_one(new_user_portfolio)

        flask_login.login_user(
            User(new_user["user_id"], email, username, new_user["portfolio_id"])
        )
        return redirect(url_for("portfolio"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = db.users.find_one({"email": email})

        if user and bcrypt.check_password_hash(user["password"], password):
            username = user["username"]
            flask_login.login_user(
                User(user["user_id"], email, username, user["portfolio_id"])
            )
            return redirect(url_for("portfolio"))
        flash("Invalid credentials", "error")
    return render_template("login.html")


@app.route("/logout")
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return redirect(url_for("login"))


@app.route("/portfolio")
@flask_login.login_required
def portfolio():
    portfolio_id = flask_login.current_user.portfolio_id

    # 1. Get Portfolio from DB
    portfolio = db.portfolios.find_one({"portfolio_id": portfolio_id})

    # Get balance from portfolio object
    current_balance = portfolio.get("balance", 0.0) if portfolio else 0.0

    # 2. Get Real Prices for these assets
    positions = portfolio["positions"] if portfolio else {}
    print(portfolio)
    asset_ids = list(positions.keys())
    live_prices = fetch_live_prices(asset_ids)
    print(asset_ids)
    # 3. Calculate Stats
    portfolio_display = []
    total_value = 0
    total_pnl = 0.0  # Track total profit/loss

    for asset_id, info in positions.items():
        side = info.get("side", "YES").upper()

        # Use live price if available; choose the value that aligns with the side's avg
        live_price_val = live_prices.get(asset_id)
        current_price = info["avg_price"]
        if live_price_val is not None:
            try:
                live_price = float(live_price_val)
                # Some feeds may return the opposite side; pick the price closest to the avg
                candidate = live_price
                complement = 1 - live_price
                current_price = (
                    candidate
                    if abs(candidate - info["avg_price"])
                    <= abs(complement - info["avg_price"])
                    else complement
                )
            except (TypeError, ValueError):
                current_price = info["avg_price"]

        market_val = current_price * info["quantity"]
        cost_basis = info["avg_price"] * info["quantity"]
        pnl = market_val - cost_basis
        # Potential profit if the outcome resolves in the user's favor
        potential_profit = max((1 - info["avg_price"]) * info["quantity"], 0.0)

        total_pnl += pnl
        total_value += market_val

        portfolio_display.append(
            {
                "market": info.get("market_question", "Unknown Market"),
                "avg_price": info["avg_price"],
                "current_price": current_price,
                "side": info.get("side", "YES"),
                "bet_amount": cost_basis,
                "quantity": info["quantity"],
                "to_win": potential_profit,
                "market_value": market_val,
                "pnl": pnl,
            }
        )

    # 4. Construct User View Data
    user_view = {
        "username": flask_login.current_user.username,
        "balance": current_balance,
        "total_value": total_value,
        "change_today": total_pnl,
    }

    # FIXED: Pass as 'user_info' instead of 'current_user' to avoid breaking base.html
    return render_template(
        "portfolio.html",
        positions=portfolio_display,
        current_user=user_view,
        current_portfolio=portfolio,
    )


@app.route("/markets")
@flask_login.login_required
def markets():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", "").strip()
    active_markets = []
    if q:
        try:
            page = page if page else 1
            resp = requests.get(
                f"{SEARCH_URL}/search", params={"q": q, "page": page}, timeout=300
            )
            data = resp.json() if resp.status_code == 200 else []
            active_markets = []
            for event in data.get("events", []):
                for m in event.get("markets", []):
                    if m.get("active") is True and m.get("closed") is False:
                        if isinstance(m.get("outcomes"), str):
                            m["outcomes"] = json.loads(m["outcomes"])
                        if isinstance(m.get("outcomePrices"), str):
                            m["outcomePrices"] = json.loads(m["outcomePrices"])
                        if isinstance(m.get("clobTokenIds"), str):
                            m["clobTokenIds"] = json.loads(m["clobTokenIds"])
                            print(m["clobTokenIds"])
                        active_markets.append(m)
                        cache_market(m["slug"], m)
        except Exception as e:
            print(e)
            flash("Search service unreachable", "error")

    return render_template("markets.html", markets=active_markets, query=q)


@app.route("/market_details")
@flask_login.login_required
def market_details():
    slug = request.args.get("slug")
    market = get_cached_market(slug)
    if not market:
        return "Market does not exist", 400
    if isinstance(market.get("outcomes"), str):
        market["outcomes"] = json.loads(market["outcomes"])
    if isinstance(market.get("outcomePrices"), str):
        market["outcomePrices"] = json.loads(market["outcomePrices"])
    if isinstance(market.get("clobTokenIds"), str):
        market["clobTokenIds"] = json.loads(market["clobTokenIds"])
        print(market["clobTokenIds"])
    # Extract clob_id from market (list of two IDs)
    asset_ids = []
    clob_id = market.get("clobTokenIds")
    if clob_id:
        # Handle both list and string formats
        if isinstance(clob_id, str):
            try:
                clob_id = json.loads(clob_id)
            except (json.JSONDecodeError, TypeError):
                clob_id = [clob_id]
        if isinstance(clob_id, list):
            asset_ids = [str(id) for id in clob_id if id]

    # Fetch historical prices (default to 1h interval)
    historical_prices = {}
    if asset_ids:
        historical_prices = fetch_historical_prices(asset_ids, interval="1h")

    return render_template(
        "market_detail.html",
        market=market,
        historical_prices=historical_prices,
        asset_ids=asset_ids,
    )


@app.route("/api/historical_prices")
@flask_login.login_required
def api_historical_prices():
    """API endpoint to fetch historical prices with interval and fidelity"""
    asset_ids = request.args.getlist("assets")
    interval = request.args.get("interval", "max")
    fidelity = request.args.get("fidelity", type=int)

    if not asset_ids:
        return jsonify({"error": "No asset IDs provided"}), 400

    # Build params for price API
    params = {"assets": asset_ids, "interval": interval}
    if fidelity is not None:
        params["fidelity"] = fidelity

    historical_prices = fetch_historical_prices(asset_ids, interval, fidelity)
    return jsonify(historical_prices)


@app.route("/live_prices", methods=["GET"])
def live_prices():
    """
    Endpoint to fetch live prices for multiple assets.
    Query parameter: ?tokens=token1,token2,token3
    Returns: JSON { "token1": price1, "token2": price2, ... }
    """
    tokens_param = request.args.get("tokens", "")
    token_ids = [t.strip() for t in tokens_param.split(",") if t.strip()]

    if not token_ids:
        return jsonify({}), 200

    prices = fetch_live_prices(token_ids)
    print("LIVE PRICES: ", prices)
    return jsonify(prices), 200


@app.route("/trade", methods=["POST"])
@flask_login.login_required
def trade():
    data = request.get_json()
    asset_id = data.get("asset_id")
    bid = data.get("bid")
    question = data.get("question")
    side = (data.get("side") or "YES").upper()
    if side not in ("YES", "NO"):
        side = "YES"

    if not all([asset_id, bid, question]):
        flash("Missing trade parameters.", "error")
        return jsonify({"success": False})

    try:
        bid = float(bid)
        if bid <= 0:
            flash("Bid must be positive.", "error")
            return jsonify({"success": False})
    except ValueError:
        flash("Invalid bid amount.", "error")
        return jsonify({"success": False})

    portfolio_id = flask_login.current_user.portfolio_id
    try:
        portfolio = db.portfolios.find_one({"portfolio_id": portfolio_id})
        print(portfolio)
    except Exception as e:
        flash(
            "Portfolio not found for the current user. Please log in again.",
            f"error: {e}",
        )
        return jsonify({"success": False, "redirect": url_for("logout")})

    try:
        # Get current execution price from the pricing service
        price = fetch_live_prices([asset_id])
        raw_price = price.get(asset_id)
        if raw_price is None:
            flash("Could not get a current price for the market.", "error")
            return jsonify({"success": False})
        try:
            raw_price = float(raw_price)
        except (TypeError, ValueError):
            flash("Received an invalid price for the market.", "error")
            return jsonify({"success": False})

        # Use the fetched price directly for the selected side token
        execution_price = raw_price

        # Calculate quantity for the selected side
        # Price represents the probability (YES or NO depending on side); bid is the cost.
        quantity = bid / execution_price

        # Deduct cost atomically
        # This update only proceeds if the balance is sufficient.
        result = db.portfolios.update_one(
            {
                "portfolio_id": portfolio_id,
                "balance": {"$gte": bid},
            },  # ensure enough balance
            {"$inc": {"balance": -bid}},
        )

        if result.matched_count == 0:
            flash("Insufficient funds. Trade aborted.", "error")
            return jsonify({"success": False, "redirect": url_for("portfolio")})

        # --- START: Modification to update current_user balance ---
        # Refetch the updated portfolio to get the new balance
        updated_portfolio = db.portfolios.find_one({"portfolio_id": portfolio_id})

        # Update the Flask-Login User object's balance property
        if updated_portfolio:
            flask_login.current_user.balance = updated_portfolio["balance"]
        # --- END: Modification to update current_user balance ---

        # Update or create the position
        current_position = db.portfolios.find_one(
            {"portfolio_id": portfolio_id, f"positions.{asset_id}": {"$exists": True}},
        )

        if current_position:
            # Position exists: calculate new average price and total cost
            existing_pos = current_position["positions"][asset_id]
            existing_cost = existing_pos["total_cost"]
            existing_shares = existing_cost / existing_pos["avg_price"]
            position_side = side

            new_total_cost = existing_cost + bid
            new_total_shares = existing_shares + quantity
            new_avg_price = new_total_cost / new_total_shares

            # Update the existing position
            db.portfolios.update_one(
                {"portfolio_id": portfolio_id},
                {
                    "$set": {
                        f"positions.{asset_id}.side": position_side,
                        f"positions.{asset_id}.total_cost": new_total_cost,
                        f"positions.{asset_id}.avg_price": new_avg_price,
                        f"positions.{asset_id}.updated_at": datetime.now(timezone.utc),
                        f"positions.{asset_id}.quantity": new_total_shares,
                    }
                },
            )
        else:
            # Position does not exist: create new one
            db.portfolios.update_one(
                {"portfolio_id": portfolio_id},
                {
                    "$set": {
                        f"positions.{asset_id}": {
                            "market_question": question,
                            "side": side,
                            "quantity": quantity,
                            "total_cost": bid,
                            "avg_price": execution_price,
                            "created_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc),
                        }
                    }
                },
                upsert=True,
            )

        flash(
            f"Executed bid ${bid:.2f}. Bought {quantity:.2f} shares at ${execution_price:.4f}",
            "success",
        )
        return jsonify({"success": True, "redirect": url_for("portfolio")})
    except Exception as e:
        print(f"Error in trade: {e}")
        flash("An unexpected error occurred during the trade.", "error")
        return jsonify({"success": False, "redirect": url_for("portfolio")})


@app.route("/settings", methods=["GET", "POST"])
@flask_login.login_required
def settings():
    if request.method == "POST":
        action = request.form.get("action", "update_profile")

        if action == "reset_account":
            reset_balance_raw = request.form.get("reset_starting_balance", "").strip()
            try:
                new_balance = int(reset_balance_raw)
            except (TypeError, ValueError):
                flash("Starting balance must be between 1 and 1,000,000.", "error")
                return redirect(url_for("settings"))

            if not 1 <= new_balance <= 1_000_000:
                flash("Starting balance must be between 1 and 1,000,000.", "error")
                return redirect(url_for("settings"))

            result = db.portfolios.update_one(
                {"portfolio_id": flask_login.current_user.portfolio_id},
                {
                    "$set": {
                        "balance": new_balance,
                        "positions": {},
                        "transaction_history": {},
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )

            if result.matched_count == 0:
                flash("Portfolio not found for reset.", "error")
                return redirect(url_for("settings"))

            flask_login.current_user.balance = new_balance
            flash("Account reset completed.", "success")
            return redirect(url_for("settings"))

        # Default profile update path
        username = request.form.get("username", "").strip()
        if not 3 <= len(username) <= 24:
            flash("Username must be 3-24 characters.", "error")
            return redirect(url_for("settings"))

        db.users.update_one(
            {"user_id": flask_login.current_user.id}, {"$set": {"username": username}}
        )
        flask_login.current_user.username = username
        flash("Updated", "success")

    portfolio = db.portfolios.find_one(
        {"portfolio_id": flask_login.current_user.portfolio_id}
    )
    current_balance = portfolio.get("balance", 0.0) if portfolio else 0.0

    return render_template("settings.html", current_balance=current_balance)


if __name__ == "__main__":
    # Detect environment: "production" vs "development"
    ENV = os.environ.get("FLASK_ENV", "development")

    if ENV == "production":
        # Docker / DigitalOcean mode
        app.run(host="0.0.0.0", port=5000, debug=False)
    else:
        # Local development mode
        app.run(debug=True)
