import os
import re
import uuid
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

from flask import Flask, abort, redirect, render_template, request, url_for, flash
import flask_login
from flask_bcrypt import Bcrypt
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)

app.secret_key = os.getenv("SECRET_KEY", "dev_secret")
MARKET_SERVICE_URL = os.getenv("MARKET_SERVICE_URL", "http://localhost:8001")
MONGO_URI = os.getenv("MONGO_URI")

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client["polypaper"]
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    raise e


class User(flask_login.UserMixin):
    def __init__(self, user_id, email, username, balance=0.0):
        self.id = user_id
        self.email = email
        self.username = username
        self.balance = balance

@login_manager.user_loader
def load_user(user_id):
    u = db.users.find_one({"user_id": user_id})
    if u:
        return User(u["user_id"], u["email"], u["username"], u.get("balance", 0.0))
    return None

def fetch_live_prices(token_ids):
    if not token_ids:
        return {}
    try:
        resp = requests.post(f"{MARKET_SERVICE_URL}/clob/prices", json={"tokens": token_ids})
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Price Fetch Error: {e}")
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
        balance = request.form.get("balance",1000.00)
        if db.users.find_one({"email": email}):
            flash("Email exists", "error")
            return redirect(url_for("register"))

        new_user = {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "username": username,
            "password": bcrypt.generate_password_hash(password).decode("utf-8"),
            "balance": starting_balance, 
            "created_at": datetime.now(timezone.utc),
        }
        db.users.insert_one(new_user)
        flask_login.login_user(User(new_user["user_id"], email, username, 1000.0))
        return redirect(url_for("portfolio"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = db.users.find_one({"email": email})
        
        if user and bcrypt.check_password_hash(user["password"], password):
            flask_login.login_user(User(user["user_id"], user["email"], user["username"], user.get("balance", 0.0)))
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
    user_id = flask_login.current_user.id
    
    # 1. Get Positions from DB
    positions = list(db.positions.find({"user_id": user_id}))
    
    # 2. Get Real Prices for these assets
    asset_ids = [p["asset_id"] for p in positions]
    live_prices = fetch_live_prices(asset_ids)

    # 3. Calculate Stats
    portfolio_display = []
    total_value = flask_login.current_user.balance
    total_pnl = 0.0 # Track total profit/loss
    
    for pos in positions:
        aid = pos["asset_id"]
        # Use live price if available, else fallback to avg_price
        current_price = live_prices.get(aid, pos["avg_price"])
        
        market_val = current_price * pos["quantity"]
        cost_basis = pos["avg_price"] * pos["quantity"]
        pnl = market_val - cost_basis
        
        total_pnl += pnl
        total_value += market_val
        
        portfolio_display.append({
            "market": pos.get("market_question", "Unknown Market"),
            "avg_price": pos["avg_price"],
            "current_price": current_price,
            "bet_amount": cost_basis,
            "quantity": pos["quantity"],
            "to_win": pnl 
        })

    # 4. Construct User View Data
    user_view = {
        "username": flask_login.current_user.username,
        "balance": flask_login.current_user.balance,
        "total_value": total_value,
        "change_today": total_pnl  # <--- FIXED: Added this key
    }

    # FIXED: Pass as 'user_info' instead of 'current_user' to avoid breaking base.html
    return render_template("portfolio.html", positions=portfolio_display, current_user=user_view)

@app.route("/markets")
@flask_login.login_required
def markets():
    q = request.args.get("q", "crypto").strip() or "crypto"
    try:
        resp = requests.get(f"{MARKET_SERVICE_URL}/search", params={"q": q, "page": 1})
        markets_data = resp.json() if resp.status_code == 200 else []
    except:
        markets_data = []
        flash("Market service unreachable", "error")

    return render_template("markets.html", markets=markets_data, query=q)

@app.route("/trade", methods=["POST"])
@flask_login.login_required
def trade():
    """Execute a simulated trade based on real market prices."""
    asset_id = request.form.get("asset_id")
    quantity = float(request.form.get("amount", 0))
    question = request.form.get("question", "Market")

    if quantity <= 0:
        flash("Invalid quantity", "error")
        return redirect(url_for("markets"))

    # 1. Get Real Price
    prices = fetch_live_prices([asset_id])
    execution_price = prices.get(asset_id)

    if not execution_price:
        flash("Could not fetch price. Trade aborted.", "error")
        return redirect(url_for("markets"))

    cost = execution_price * quantity

    # 2. Check Balance
    if flask_login.current_user.balance < cost:
        flash(f"Insufficient funds. Cost: ${cost:.2f}", "error")
        return redirect(url_for("portfolio"))

    # 3. Execute (Update DB)
    db.users.update_one(
        {"user_id": flask_login.current_user.id},
        {"$inc": {"balance": -cost}}
    )

    # Upsert position
    existing = db.positions.find_one({"user_id": flask_login.current_user.id, "asset_id": asset_id})
    if existing:
        # Calculate new weighted average
        old_q = existing["quantity"]
        old_avg = existing["avg_price"]
        new_q = old_q + quantity
        new_avg = ((old_q * old_avg) + cost) / new_q
        
        db.positions.update_one(
            {"_id": existing["_id"]},
            {"$set": {"quantity": new_q, "avg_price": new_avg}}
        )
    else:
        db.positions.insert_one({
            "user_id": flask_login.current_user.id,
            "asset_id": asset_id,
            "market_question": question,
            "quantity": quantity,
            "avg_price": execution_price
        })

    flash(f"Bought {quantity} shares at {execution_price}", "success")
    return redirect(url_for("portfolio"))

@app.route("/settings", methods=["GET", "POST"])
@flask_login.login_required
def settings():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        db.users.update_one({"user_id": flask_login.current_user.id}, {"$set": {"username": username}})
        flask_login.current_user.username = username
        flash("Updated", "success")
    return render_template("settings.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
