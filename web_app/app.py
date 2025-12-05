from flask import Flask, render_template, redirect, url_for, request

app = Flask(__name__)


@app.route("/")
def home():
    return redirect(url_for("portfolio"))


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


if __name__ == "__main__":
    app.run(debug=True)
