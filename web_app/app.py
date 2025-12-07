import os
import re
import uuid
from dotenv import load_dotenv
from datetime import datetime, timezone

from flask import Flask, abort, redirect, render_template, request, url_for, flash
import flask_login
from flask_bcrypt import Bcrypt
from pymongo import MongoClient

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
bcrypt = Bcrypt(app)

# Initialize Flask-Login
app.secret_key = os.getenv("SECRET_KEY")
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

# Initialize MongoDB client
try:
    mongo_client = MongoClient(os.getenv("MONGO_URI"))
    db = mongo_client["polypaper"]
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    raise e


class User(flask_login.UserMixin):
    def __init__(self, user_id, email, username, group_id):
        self.id = user_id
        self.email = email
        self.username = username
        self.group_id = group_id


@login_manager.user_loader
def load_user(user_id):
    try:
        response = db.users.find_one({"user_id": user_id})
        if response is not None:
            return User(
                user_id=response["user_id"],
                email=response["email"],
                username=response["username"],
                group_id=response["group_id"],
            )
        return None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None


@app.route("/")
def home():
    if flask_login.current_user.is_authenticated:
        return redirect(url_for("portfolio"))
    else:
        return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Validate the form data
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not email:
            flash("Email is required", "error")
            return render_template("register.html")
        if not username:
            flash("Username is required", "error")
            return render_template("register.html")
        if not password:
            flash("Password is required", "error")
            return render_template("register.html")
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("register.html")

        # Check if email is already in use
        existing_email = db.users.find_one({"email": email})
        if existing_email:
            flash("Email is already registered", "error")
            return render_template("register.html")

        # Check if username is already in use
        existing_username = db.users.find_one({"username": username})
        if existing_username:
            flash("Username is already taken", "error")
            return render_template("register.html")

        # Validate password complexity
        # Password must contain: at least 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special character
        if len(password) < 8:
            flash("Password must be at least 8 characters long", "error")
            return render_template("register.html")
        if not re.search(r"[A-Z]", password):
            flash("Password must contain at least one uppercase letter", "error")
            return render_template("register.html")
        if not re.search(r"[a-z]", password):
            flash("Password must contain at least one lowercase letter", "error")
            return render_template("register.html")
        if not re.search(r"\d", password):
            flash("Password must contain at least one number", "error")
            return render_template("register.html")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            flash(
                'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)',
                "error",
            )
            return render_template("register.html")

        """MongoDB `users` collection schema
        users:
            user_id: uuid,
            email: string,
            username: string,
            password: hash,
            group_id: uuid,
            created_at: UTC timestamp,
            deleted_at: UTC timestamp,
        """
        new_user_data = {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "username": username,
            "password": password,
            "group_id": 0,  # placeholder until we implement groups
            "created_at": datetime.now(timezone.utc),
            "deleted_at": None,
        }

        # User passwords are stored as hashes in the database
        password_hash = bcrypt.generate_password_hash(new_user_data["password"]).decode(
            "utf-8"
        )
        new_user_data["password"] = password_hash

        try:
            db.users.insert_one(new_user_data)
        except Exception as e:
            print(f"Error inserting user: {e}")
            flash(f"Error creating account: {e}", "error")
            return render_template("register.html")

        # Log the user in using Flask-Login
        flask_login.login_user(
            User(
                user_id=new_user_data["user_id"],
                email=email,
                username=username,
                group_id=0,  # placeholder until we implement groups
            )
        )

        flash(
            f"{new_user_data['username']} account has been created successfully",
            "success",
        )
        return redirect(url_for("portfolio"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Check if the user exists and the password is correct
        user = db.users.find_one({"email": email})
        if user and bcrypt.check_password_hash(user["password"], password):
            flask_login.login_user(
                User(
                    user_id=user["user_id"],
                    email=email,
                    username=user["username"],
                    group_id=user["group_id"],
                )
            )
            return redirect(url_for("portfolio"))
        else:
            flash("Invalid email or password", "error")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
@flask_login.login_required
def logout():
    flask_login.logout_user()
    flash("You have been logged out", "success")
    return redirect(url_for("login"))


@app.route("/portfolio")
@flask_login.login_required
def portfolio():
    # Placeholder until portfolio is implemented
    user = {
        "username": flask_login.current_user.username,
        "balance": 1000.00,
        "change_today": 25.50,
    }

    positions = [
        {
            "market": "Will BTC be above $100k by 2026?",
            "avg_price": 0.40,
            "current_price": 0.55,
            "bet_amount": 200.00,
            "to_win": 110.00,
        },
        {
            "market": "Will candidate X win the 2028 election?",
            "avg_price": 0.60,
            "current_price": 0.45,
            "bet_amount": 150.00,
            "to_win": -37.50,
        },
    ]

    return render_template("portfolio.html", positions=positions, current_user=user)


# TEMP shared mock data
ALL_MARKETS = [
    {
        "id": 1,
        "question": "Will BTC close above $80k on Dec 31, 2025?",
        "region": "Global",
        "category": "Crypto",
        "yes_price": 0.42,
        "volume_24h": 12500,
    },
    {
        "id": 2,
        "question": "Will NYC record snowfall before Jan 15, 2026?",
        "region": "USA",
        "category": "Weather",
        "yes_price": 0.28,
        "volume_24h": 2100,
    },
    {
        "id": 3,
        "question": "Will the S&P 500 end 2025 higher than it started?",
        "region": "USA",
        "category": "Indices",
        "yes_price": 0.63,
        "volume_24h": 8300,
    },
]


@app.route("/markets")
@flask_login.login_required
def markets():
    q = request.args.get("q", "").strip().lower()
    if q:
        markets = [
            m
            for m in ALL_MARKETS
            if q in m["question"].lower()
            or q in m["region"].lower()
            or q in m["category"].lower()
        ]
    else:
        markets = ALL_MARKETS

    return render_template("markets.html", markets=markets, query=q)


@app.route("/markets/<int:market_id>")
@flask_login.login_required
def market_detail(market_id: int):
    market = next((m for m in ALL_MARKETS if m["id"] == market_id), None)
    if market is None:
        abort(404)
    return render_template("market_detail.html", market=market)


@app.route("/settings", methods=["GET", "POST"])
@flask_login.login_required
def settings():
    if request.method == "POST":
        username = request.form.get("username", "").strip()

        # Validate username
        if not username:
            flash("Username is required", "error")
            return render_template("settings.html")

        if len(username) < 3:
            flash("Username must be at least 3 characters", "error")
            return render_template("settings.html")

        if len(username) > 24:
            flash("Username cannot exceed 24 characters", "error")
            return render_template("settings.html")

        # Check if username is already taken by another user
        existing_user = db.users.find_one({"username": username})
        if existing_user and existing_user["user_id"] != flask_login.current_user.id:
            flash("Username is already taken", "error")
            return render_template("settings.html")

        # Update username in database
        try:
            db.users.update_one(
                {"user_id": flask_login.current_user.id},
                {"$set": {"username": username}},
            )

            # Update the current user object
            flask_login.current_user.username = username

            flash("Username updated successfully", "success")
            return redirect(url_for("settings"))
        except Exception as e:
            print(f"Error updating username: {e}")
            flash(f"Error updating username: {str(e)}", "error")
            return render_template("settings.html")

    # GET request - render settings page
    return render_template("settings.html")


if __name__ == "__main__":
    app.run(debug=True)
