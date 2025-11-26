# main_app.py
import panel as pn
import pandas as pd
import urllib.parse as urlparse

from tab_dashboard import create_dashboard_view
from tab_forecast import create_forecast_view
from tab_recommendation import create_recommendation_view

# ================== LOAD REAL CSV ==================
df_all = pd.read_csv("df_continent.csv")

df_all = df_all.dropna(subset=["Country", "Year", "Co2_MtCO2", "Co2_Capita_tCO2"])
df_all["Year"] = df_all["Year"].astype(int)

# ================== CSS UI ==================
CUSTOM_CSS = """
body {
    background-color: #f7fbf8;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.app-title {
    font-size: 28px;
    font-weight: 700;
    color: #147a3c;
    margin-bottom: 0.2rem;
}
.top-nav {
    display: flex;
    gap: 1rem;
    margin-top: 1rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid #e0e0e0;
}
.nav-item,
.nav-item-active {
    display: inline-block;
    padding: 0.6rem 1.4rem;
    border-radius: 999px 999px 0 0;
    font-size: 13px;
    font-weight: 500;
    text-decoration: none;
}
.nav-item {
    color: #6b7280;
}
.nav-item-active {
    background-color: #147a3c;
    color: white;
}
.filter-label {
    font-size: 11px;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 0.15rem;
    letter-spacing: 0.08em;
}
.kpi-card {
    background: #eaf7ef;
    padding: 1.1rem 1.3rem;
    border-radius: 16px;
    border: 1px solid #d0ead9;
    min-height: 90px;
}
.kpi-label {
    font-size: 12px;
    color: #6b7280;
}
.kpi-value {
    font-size: 22px;
    font-weight: 700;
    color: #111;
}

/* ==== PERIOD VALUE PILL: "2010 → 2020" ==== */
.period-pill {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 999px;
    background: #e6f7ed;
    color: #147a3c;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.06em;
    margin-bottom: 4px;
}

/* ==== SLIDER STYLE ==== */
.bk-slider {
    padding-top: 4px;
}
.bk-slider .noUi-base {
    background: linear-gradient(90deg, #e6f7ed 0%, #f2fcf8 100%);
    height: 10px;
    border-radius: 12px;
}
.bk-slider .noUi-connect {
    background: linear-gradient(90deg, #33cc7a 0%, #4ddf8d 100%);
    height: 10px;
    border-radius: 12px;
}
.bk-slider .noUi-handle {
    background: #ffffff;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    border: 2px solid #2ebf74;
    box-shadow:
        0 2px 4px rgba(0,0,0,0.15),
        0 0 4px rgba(46,191,116,0.6);
    cursor: pointer;
}
.bk-slider .noUi-handle:hover {
    transform: scale(1.08);
}

/* ===== Forecast model toggle (GRU / XGBoost) – style chung cho bk-btn-group ===== */

/* khung group */
.bk-btn-group {
    display: flex;
    width: 100%;
    border-radius: 999px;
    overflow: hidden;
    background: transparent;
    box-shadow: none;
    border: none;
    padding: 0;
    margin: 0;
}

/* từng nút bên trong */
.bk-btn-group > .bk-btn {
    flex: 1 1 0;
    border-radius: 0;
    background: #f1f5f9 !important;   /* xám nhạt */
    color: #374151 !important;
    border: 1px solid #e5e7eb !important;
    box-shadow: none !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 0.6rem 1rem !important;
    transition: background 0.15s ease, color 0.15s ease !important;
}

/* hover */
.bk-btn-group > .bk-btn:hover {
    background: #e2e8f0 !important;
    color: #111827 !important;
}

/* nút đang được chọn */
.bk-btn-group > .bk-btn.bk-active {
    background: #16a34a !important;   /* xanh lá đồng bộ nav/slider */
    border-color: #15803d !important;
    color: #ffffff !important;
    box-shadow: 0 3px 6px rgba(0,0,0,0.15) !important;
}

/* bỏ outline khi focus */
.bk-btn-group > .bk-btn:focus {
    outline: none !important;
    box-shadow: none !important;
}
"""

pn.extension('tabulator', sizing_mode="stretch_width", raw_css=[CUSTOM_CSS])

title = pn.pane.HTML('<div class="app-title">CO₂ Emission</div>')

# ================== NAV + ROUTER  ==================
location = pn.state.location

def get_page_from_search(search: str) -> str:
    if not search or len(search) <= 1:
        return "dashboard"
    qs = urlparse.parse_qs(search.lstrip("?"))
    return qs.get("page", ["dashboard"])[0]

def nav_view(search):
    page = get_page_from_search(search)

    def cls(name: str) -> str:
        return "nav-item-active" if page == name else "nav-item"

    html = f"""
<div class="top-nav">
  <a class="{cls('dashboard')}" href="?page=dashboard">Dashboard</a>
  <a class="{cls('forecast')}" href="?page=forecast">Forecast CO₂ Emission</a>
  <a class="{cls('recommend')}" href="?page=recommend">Recommendation Engine</a>
</div>
"""
    return pn.pane.HTML(html, sizing_mode="stretch_width")

nav = pn.bind(nav_view, location.param.search)

def router(search):
    page = get_page_from_search(search)
    if page == "forecast":
        return create_forecast_view(df_all)
    elif page == "recommend":
        return create_recommendation_view()
    else:
        return create_dashboard_view(df_all)

body = pn.bind(router, location.param.search)

# ================== FINAL APP ==================
app = pn.Column(
    title,
    nav,
    pn.Spacer(height=10),
    body,
)

app.servable("CO₂ Emission Dashboard")
