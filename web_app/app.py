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
    if u:
        return User(u["user_id"], u["email"], u["username"], u["portfolio_id"])
    return None


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

    try:
        # CLOB expects a GET request with query parameters, not POST
        params = {"tokens": ",".join(token_ids)}
        resp = requests.get(f"{PRICE_SERVICE_URL}/clob", params=params, timeout=5)
        resp.raise_for_status()  # raise exception for 4xx/5xx responses

        data = resp.json()
        # Convert to mapping asset_id -> mid_price
        prices = {token_ids[i]: data[i] for i in range(len(token_ids))}
        return prices
    except requests.RequestException as e:
        print(f"Price Fetch Error: {e}")
        return {}
    except (ValueError, KeyError, TypeError) as e:
        print(f"Data parsing error: {e}")
        return {}


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
        starting_balance = float(request.form.get("balance", 0.0))
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

    # 1. Get Positions from DB
    portfolio = db.portfolios.find_one({"portfolio_id": portfolio_id})

    # 2. Get Real Prices for these assets
    positions = portfolio["positions"]
    asset_ids = [p["asset_id"] for p in positions]
    live_prices = fetch_live_prices(asset_ids)

    # 3. Calculate Stats
    portfolio_display = []
    total_value = flask_login.current_user.balance
    total_pnl = 0.0  # Track total profit/loss

    for pos in positions:
        aid = pos["asset_id"]
        # Use live price if available, else fallback to avg_price
        current_price = live_prices.get(aid, pos["avg_price"])

        market_val = current_price * pos["quantity"]
        cost_basis = pos["avg_price"] * pos["quantity"]
        pnl = market_val - cost_basis

        total_pnl += pnl
        total_value += market_val

        portfolio_display.append(
            {
                "market": pos.get("market_question", "Unknown Market"),
                "avg_price": pos["avg_price"],
                "current_price": current_price,
                "bet_amount": cost_basis,
                "quantity": pos["quantity"],
                "to_win": pnl,
            }
        )

    # 4. Construct User View Data
    user_view = {
        "username": flask_login.current_user.username,
        "balance": flask_login.current_user.balance,
        "total_value": total_value,
        "change_today": total_pnl,
    }

    # FIXED: Pass as 'user_info' instead of 'current_user' to avoid breaking base.html
    return render_template(
        "portfolio.html", positions=portfolio_display, current_user=user_view
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
    """Execute a simulated trade based on real market prices."""
    try:
        data = request.get_json(force=True)
        print(data)
        asset_id = data.get("asset_id")
        bid = float(data.get("bid", 0))
        question = data.get("question")

        if bid <= 0:
            flash("Invalid bid", "error")
            return jsonify({"success": False, "redirect": url_for("markets")})

        # 1. Get Real Price
        prices = fetch_live_prices([asset_id])
        execution_price = float(prices.get(asset_id))
        quantity = bid / execution_price
        if not execution_price:
            flash("Could not fetch price. Trade aborted.", "error")
            return jsonify({"success": False, "redirect": url_for("markets")})

        # 2. Check Balance
        if flask_login.current_user.balance < bid:
            flash(f"Insufficient funds. Cost: ${bid:.2f}", "error")
            return jsonify({"success": False, "redirect": url_for("portfolio")})
        portfolio_id = flask_login.current_user.portfolio_id
        # 3. Deduct cost atomically
        result = db.portfolios.update_one(
            {"_id": portfolio_id, "balance": {"$gte": bid}},  # ensure enough balance
            {"$inc": {"balance": -bid}},
        )
        if result.matched_count == 0:
            flash("Insufficient funds. Trade aborted.", "error")
            return jsonify({"success": False, "redirect": url_for("portfolio")})

        current_position = db.portfolios.find_one(
            {"_id": portfolio_id, f"positions.{asset_id}": {"$exists": True}},
            {f"positions.{asset_id}": 1},
        )
        if current_position:
            # Asset exists → calculate new weighted average
            old_q = current_position["positions"][asset_id]["quantity"]
            old_avg = current_position["positions"][asset_id]["avg_price"]
            new_q = old_q + quantity
            new_avg = ((old_q * old_avg) + (quantity * execution_price)) / new_q

            db.portfolios.update_one(
                {"_id": portfolio_id},
                {
                    "$set": {
                        f"positions.{asset_id}.quantity": new_q,
                        f"positions.{asset_id}.avg_price": new_avg,
                    }
                },
            )
        else:
            db.portfolios.update_one(
                {"_id": portfolio_id},
                {
                    "$set": {
                        f"positions.{asset_id}": {
                            "market_question": question,
                            "quantity": quantity,
                            "avg_price": execution_price,
                        }
                    }
                },
                upsert=True,
            )

        flash(
            f"Executed bid {bid}. Bought {quantity} shares at {execution_price}",
            "success",
        )
    except Exception as e:
        print(f"Error in trade: {e}")
    return jsonify({"success": True, "redirect": url_for("portfolio")})


# TEMP: pretend the user has these markets on their watchlist
WATCHLIST_MARKET_IDS = [1, 3]


@app.route("/watchlist")
@flask_login.login_required
def watchlist():
    watchlist_markets = [m for m in ALL_MARKETS if m["id"] in WATCHLIST_MARKET_IDS]

    return render_template("watchlist.html", markets=watchlist_markets)


@app.route("/settings", methods=["GET", "POST"])
@flask_login.login_required
def settings():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        db.users.update_one(
            {"user_id": flask_login.current_user.id}, {"$set": {"username": username}}
        )
        flask_login.current_user.username = username
        flash("Updated", "success")
    return render_template("settings.html")


if __name__ == "__main__":
    # Detect environment: "production" vs "development"
    ENV = os.environ.get("FLASK_ENV", "development")

    if ENV == "production":
        # Docker / DigitalOcean mode
        app.run(host="0.0.0.0", port=5000, debug=False)
    else:
        # Local development mode
        app.run(debug=True)
