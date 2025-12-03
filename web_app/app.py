from flask import Flask, render_template, redirect, url_for 

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

if __name__ == "__main__":
    app.run(debug=True)
