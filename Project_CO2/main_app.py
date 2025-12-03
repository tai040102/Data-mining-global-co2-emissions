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
    margin: 0;
    padding: 0 40px 32px 40px;  /* 👈 padding hai bên + phía dưới */
    box-sizing: border-box;
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

/* ==== Global style cho Panel buttons (Run Prediction) ==== */
button.bk.bk-btn {
    background-color: #2fa24f !important;   /* xanh lá */
    color: #ffffff !important;
    border-radius: 999px !important;
    padding: 8px 24px !important;
    font-weight: 600 !important;
    border: none !important;
    box-shadow: 0 3px 6px rgba(0,0,0,0.15) !important;
    transition: 0.2s ease-in-out;
}

button.bk.bk-btn:hover {
    background-color: #25833f !important;
    transform: translateY(-1px);
    box-shadow: 0 5px 10px rgba(0,0,0,0.20) !important;
}

button.bk.bk-btn:active {
    transform: translateY(0);
    box-shadow: none !important;
}
/* STYLE TAGS FOR MULTICHOICE (COMPARE) */
.bk-tag {
    background-color: #147a3c !important;   /* xanh lá chủ đạo */
    color: white !important;
    border-radius: 6px !important;
    padding: 4px 8px !important;
    font-weight: 600 !important;
    border: none !important;
}

/* nút X */
.bk-tag button {
    color: white !important;
    font-weight: bold !important;
}

/* hover hiệu ứng nhẹ */
.bk-tag:hover {
    background-color: #0f5f2d !important;
}
.choices__list--multiple .choices__item {
    background-color: #147a3c !important;   /* xanh lá chủ đạo */
    color: #ffffff !important;
    border-radius: 10px !important;
    padding: 3px 8px !important;
}
.pie-legend {
    display: inline-flex;
    gap: 16px;
    align-items: center;
    padding: 4px 12px;
    border-radius: 8px;
    background: white;
    box-shadow: 0 0 6px rgba(0,0,0,0.04);
    margin-top: 4px;
}

.pie-legend-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
}

.pie-legend-color {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    display: inline-block;
}

/* ======================= RECOMMENDATION TAB ======================= */

/* header "Recommendation Engine" */
.rec-header {
    font-size: 20px;
    font-weight: 700;
    color: #147a3c;
    margin-bottom: 0.5rem;
}

/* hàng country / year / target */
.rec-top-row {
    margin-top: 4px;
    margin-bottom: 10px;
    align-items: flex-end;
}

/* hộp select và input phía trên */
.rec-select .bk-input,
.rec-target-input .bk-input {
    border-radius: 999px !important;
    border: 1px solid #d1d5db !important;
    box-shadow: none !important;
    padding: 4px 12px !important;
    font-size: 13px !important;
    min-width: 150px;
}
.rec-target-input .bk-input input {
    text-align: center;
    font-weight: 600;
}

/* panel trái */
.rec-left-panel {
    background: #ffffff;
    border-radius: 18px;
    padding: 18px 20px 20px 20px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 6px 18px rgba(0,0,0,0.03);
}

/* layout chính của tab */
.rec-main-row {
    margin-top: 10px;
    align-items: flex-start;
}

/* header của bảng feature */
.rec-feature-header {
    background: #e6f7ed;
    border-radius: 12px 12px 0 0;
    padding: 8px 10px;
    border: 1px solid #cdebd8;
    font-size: 13px;
    font-weight: 600;
}

/* grid chứa các dòng feature */
.rec-feature-grid {
    background: #f7fbf8;
    border-radius: 0 0 12px 12px;
    padding: 6px 10px 10px 10px;
    border: 1px solid #cdebd8;
    border-top: none;
    font-size: 13px;
}

/* căn lại checkbox trong bảng */
.rec-feature-grid .bk-checkbox {
    display: flex;
    justify-content: center;
    align-items: center;
}

/* ô data 2025 / 2026 */
.rec-data-cell .bk-input {
    border-radius: 999px !important;
    border: 1px solid #d1d5db !important;
    padding: 2px 10px !important;
    font-size: 12px !important;
    height: 30px;
}

/* slider giảm / tăng trong bảng đã được global .bk-slider style */

/* khối Recommend bên dưới bảng */
.rec-recommend-block {
    margin-top: 8px;
}

/* text kết quả Recommend */
.rec-result-text {
    font-size: 13px;
}
.rec-result-text ul {
    margin-top: 4px;
}

/* card bên phải: Predict CO2 */
.rec-predict-card {
    background: #f3fbf6 !important;
    border-radius: 18px !important;
    border: 1px solid #d4ecdd !important;
    box-shadow: 0 6px 18px rgba(0,0,0,0.03) !important;
    padding: 16px !important;
}

/* input trong Predict card */
.rec-predict-input .bk-input {
    border-radius: 999px !important;
    border: 1px solid #d1d5db !important;
    padding: 3px 12px !important;
    font-size: 13px !important;
    margin-bottom: 6px;
}

/* kết quả Predict */
.rec-predict-result {
    font-size: 13px;
    text-align: center;
    color: #374151;
}
.rec-predict-result h3 {
    color: #147a3c;
}

/* nút Recommend / Predict (đã có style chung, chỉ căn giữa) */
.rec-recommend-btn,
.rec-predict-btn {
    margin-top: 8px;
}
.rec-feature-name {
    white-space: nowrap;
    font-weight: 500;
}
.rec-left-panel {
    background: #ffffff;
    border-radius: 18px;
    padding: 18px 20px 20px 20px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 6px 18px rgba(0,0,0,0.03);
    overflow-x: auto;   /* tránh tràn ngang */
}

/* ===== Recommendation table dùng CSS grid cho các hàng ===== */

.rec-table {
    background: #f7fbf8;
    border-radius: 12px;
    padding: 10px 16px 14px 16px;
    border: 1px solid #cdebd8;
}

/* 6 cột: checkbox | feature | data prev | slider dec | slider inc | data curr */
.rec-row {
    display: grid;
    grid-template-columns: 30px minmax(160px, 2fr) 120px minmax(180px, 3fr) minmax(180px, 3fr) 120px;
    column-gap: 16px;
    align-items: center;
    font-size: 13px;
    margin-bottom: 4px;
}

.rec-row-header {
    font-weight: 600;
    margin-bottom: 6px;
}

.rec-feature-name {
    white-space: nowrap;
}

/* số data bên trái/phải */
.rec-data-cell {
    text-align: right;
    font-size: 11px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
        return create_recommendation_view(df_all)
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
