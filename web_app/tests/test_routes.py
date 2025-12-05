from web_app.app import app


def test_portfolio_page_loads_and_shows_positions():
    """Portfolio page should render with user and two positions."""
    client = app.test_client()
    resp = client.get("/portfolio")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    # From base.html
    assert "PolyPaper" in html
    assert "Practice trading event contracts" in html

    # From portfolio.html (with positions)
    assert "Will BTC be above $100k by 2026?" in html
    assert "Will candidate X win the 2028 election?" in html

    # Profit/loss chips
    assert "value-chip positive" in html
    assert "value-chip negative" in html

    # User balance + change today
    assert "$1000.00" in html
    assert "$25.50" in html


def test_nav_links_present_on_portfolio():
    """Top nav tabs should render correctly."""
    client = app.test_client()
    resp = client.get("/portfolio")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    assert "Portfolio" in html
    assert "Markets" in html
    assert "Watchlist" in html


def test_root_redirects_to_portfolio():
    client = app.test_client()
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (301, 302)


def test_markets_page_loads():
    client = app.test_client()
    resp = client.get("/markets")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    # Page title + subtitle
    assert "Markets" in html
    assert "Search for event markets and practice trading without the risk." in html

    # Market cards
    assert "Open market" in html
    assert "Will BTC close above $80k on Dec 31, 2025?" in html


def test_market_detail_page_loads():
    client = app.test_client()
    resp = client.get("/markets/1")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    # page content
    assert "Will BTC close above $80k on Dec 31, 2025?" in html
    assert "Crypto" in html

    # trade ticket title
    assert "Place a paper trade" in html
