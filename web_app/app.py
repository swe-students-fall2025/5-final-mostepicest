from flask import Flask, abort, redirect, render_template, request, url_for


app = Flask(__name__)


@app.context_processor
def inject_user_context():
    # Temporary user context so the topbar can show a username before real auth is wired up.
    return {"current_username": "demo_user"}


@app.route("/")
def home():
    return redirect(url_for("login"))  # Home is changed to the login page


@app.route("/portfolio")
def portfolio():
    user = {
        "username": "demo_user",
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

    return render_template("portfolio.html", user=user, positions=positions)


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
def market_detail(market_id: int):
    market = next((m for m in ALL_MARKETS if m["id"] == market_id), None)
    if market is None:
        abort(404)
    return render_template("market_detail.html", market=market)


@app.route("/register", methods=["GET", "POST"])
def register():
    # status_message lets the template show what would happen once persistence is added.
    status_message = None  # nothing for now

    if request.method == "POST":
        # Capture the fields we will later insert into the MongoDB users collection.
        form_data = {
            "email": request.form.get("email", "").strip(),
            "username": request.form.get("username", "").strip(),
            "password": request.form.get("password", ""),
        }

        # Placeholder response until we hook up the real thing
        status_message = (
            f"Received your details for {form_data['email'] or 'your account'} - "
            "MongoDB insert will be added when we implement the database"
        )

    return render_template("register.html", status_message=status_message)


@app.route("/login", methods=["GET", "POST"])
def login():
    # the status_message tells the user what happens after a real authentication check
    status_message = None

    if request.method == "POST":
        # Collect the credentials just like we will when we query MongoDB
        submitted_email = request.form.get("email", "").strip()
        submitted_password = request.form.get("password", "")

        # Placeholder request
        status_message = (
            f"Login submission received for {submitted_email or 'your account'} - "
            "MongoDB lookup and password verification will come in a bit"
        )
        return redirect(
            url_for("portfolio")
        )  # Redirect to portfolio after login (until real auth exists)

    return render_template("login.html", status_message=status_message)


# New settings route 
@app.route("/settings")
def settings():
    # Placeholder settings page until Mongo-backed profiles exist.
    return render_template("settings.html")


@app.route("/logout")
def logout():
    # Placeholder logout send the user back to the login page after the button is clicked.
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
