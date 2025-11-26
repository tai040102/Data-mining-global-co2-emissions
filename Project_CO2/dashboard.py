import panel as pn
import pandas as pd
from bokeh.plotting import figure
import urllib.parse as urlparse
from bokeh.models import HoverTool, ColumnDataSource

# ================== LOAD REAL CSV ==================
df_all = pd.read_csv("df_continent.csv")

df_all = df_all.dropna(subset=["Country", "Year", "Co2_MtCO2", "Co2_Capita_tCO2"])
df_all["Year"] = df_all["Year"].astype(int)

# Get data
continents = sorted(df_all["Continent"].dropna().unique())
countries_by_continent = {
    c: sorted(df_all[df_all["Continent"] == c]["Country"].unique())
    for c in continents
}
years = sorted(df_all["Year"].unique())

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
"""

pn.extension('tabulator', sizing_mode="stretch_width", raw_css=[CUSTOM_CSS])

# ================== WIDGETS ==================
continent = pn.widgets.Select(
    name="", options=continents, value=continents[0], width=220
)

country = pn.widgets.Select(
    name="", options=countries_by_continent[continents[0]], width=220
)

# Range Year Slider
period = pn.widgets.IntRangeSlider(
    name="", start=min(years), end=max(years), value=(2010, 2020),
    width=400, show_value=False
)
period.bar_color = "#33cc7a"

# Display "2010 → 2020"
period_display = pn.bind(
    lambda r: f'<div class="period-pill">{r[0]} → {r[1]}</div>',
    period
)

def update_countries(event):
    country.options = countries_by_continent[continent.value]
continent.param.watch(update_countries, "value")

def filter_block(label, widget):
    return pn.Column(
        pn.pane.HTML(f'<div class="filter-label">{label}</div>'),
        widget,
        width=260,
    )

# block riêng cho PERIOD: label + pill + slider
period_block = pn.Column(
    pn.pane.HTML('<div class="filter-label">PERIOD</div>'),
    period_display,
    period,
    width=260,
)

filters_row = pn.Row(
    filter_block("CONTINENT", continent),
    filter_block("COUNTRY", country),
    period_block,
)


# ================== KPI ==================
def humanize_gdp(gdp: float) -> str:
    if gdp is None or pd.isna(gdp):
        return "0"
    if gdp >= 1e12:
        return f"{gdp/1e12:.2f} T"
    elif gdp >= 1e9:
        return f"{gdp/1e9:.2f} B"
    elif gdp >= 1e6:
        return f"{gdp/1e6:.2f} M"
    else:
        return f"{gdp:,.0f}"

def compute_kpis(country, year_range):
    y_min, y_max = year_range
    df = df_all[
        (df_all["Country"] == country)
        & (df_all["Year"] >= y_min)
        & (df_all["Year"] <= y_max)
    ]

    if df.empty:
        return "0", "0", "0", "0", "0"

    avg_total_co2   = df["Co2_MtCO2"].mean()
    avg_capita_co2  = df["Co2_Capita_tCO2"].mean()
    avg_gdp         = df["GDP"].mean() if "GDP" in df else 0
    avg_hdi         = df["HDI"].mean() if "HDI" in df else 0
    avg_energy_cap  = df["Energy_Capita_kWh"].mean() if "Energy_Capita_kWh" in df else 0

    total_str  = f"{avg_total_co2:,.2f} Mt"
    capita_str = f"{avg_capita_co2:.5f} t"
    gdp_str    = humanize_gdp(avg_gdp)
    hdi_str    = f"{avg_hdi:.3f}"
    energy_str = f"{avg_energy_cap:,.1f}"

    return total_str, capita_str, gdp_str, hdi_str, energy_str

def kpi_card(label, value):
    html = f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
    </div>
    """
    return pn.pane.HTML(html, height=100)

def kpi_row_view(country, period):
    total, capita, gdp, hdi, energy = compute_kpis(country, period)
    return pn.Row(
        kpi_card("Total CO₂", total),
        kpi_card("CO₂ per Capita", capita),
        kpi_card("GDP", gdp),
        kpi_card("HDI", hdi),
        kpi_card("Energy per Capita (kWh)", energy),
    )

kpi_row = pn.bind(kpi_row_view, country=country, period=period)

# ================== CHARTS ==================
def chart_capita(country, year_range):
    y_min, y_max = year_range
    df = df_all[
        (df_all["Country"] == country)
        & (df_all["Year"] >= y_min)
        & (df_all["Year"] <= y_max)
    ].copy()

    source = ColumnDataSource(df[["Year", "Co2_Capita_tCO2"]])

    p = figure(height=280, sizing_mode="stretch_width",
               tools="pan,wheel_zoom,box_zoom,reset,save")

    p.line('Year', 'Co2_Capita_tCO2', source=source,
           line_width=3, color="#10b981")
    p.circle('Year', 'Co2_Capita_tCO2', source=source,
             size=6, color="#10b981")

    p.xaxis.axis_label = "Year"
    p.yaxis.axis_label = "tCO₂ per capita"

    hover = HoverTool(
        tooltips=[
            ("Year", "@Year"),
            ("CO₂ per capita", "@Co2_Capita_tCO2{0.00000} t"),
        ],
        mode="vline"
    )
    p.add_tools(hover)

    return p

def chart_total(country, year_range):
    y_min, y_max = year_range
    df = df_all[
        (df_all["Country"] == country)
        & (df_all["Year"] >= y_min)
        & (df_all["Year"] <= y_max)
    ].copy()

    source = ColumnDataSource(df[["Year", "Co2_MtCO2"]])

    p = figure(height=280, sizing_mode="stretch_width",
               tools="pan,wheel_zoom,box_zoom,reset,save")

    p.line('Year', 'Co2_MtCO2', source=source,
           line_width=3, color="#065f1f")
    p.circle('Year', 'Co2_MtCO2', source=source,
             size=6, color="#065f1f")

    p.xaxis.axis_label = "Year"
    p.yaxis.axis_label = "MtCO₂ total"

    hover = HoverTool(
        tooltips=[
            ("Year", "@Year"),
            ("Total CO₂", "@Co2_MtCO2{0,0.00} Mt"),
        ],
        mode="vline"
    )
    p.add_tools(hover)

    return p


chart_left = pn.bind(chart_capita, country=country, year_range=period)
chart_right = pn.bind(chart_total, country=country, year_range=period)

charts_row = pn.Row(
    pn.Column("### CO₂ per Capita", chart_left),
    pn.Column("### Total CO₂", chart_right),
)

# ================== PAGE COMPONENTS ==================

title = pn.pane.HTML('<div class="app-title">CO₂ Emission</div>')

def dashboard_view():
    return pn.Column(
        pn.Spacer(height=10),
        filters_row,
        pn.Spacer(height=15),
        kpi_row,
        pn.Spacer(height=20),
        charts_row,
    )

def forecast_view():
    header = pn.pane.Markdown("## Forecast CO₂ Emission")

    country_sel = pn.widgets.Select(
        name="Country", options=["Vietnam", "Thailand", "USA"], value="Vietnam"
    )
    hist_window = pn.widgets.Select(
        name="Historical Data Window",
        options=["Last 3 years", "Last 5 years"],
        value="Last 3 years",
    )
    year_sel = pn.widgets.Select(
        name="Year", options=[2026, 2027, 2028], value=2026
    )

    df_input = pd.DataFrame({
        "Year": [2023, 2024, 2025],
        "CO₂ Emission (Mt)": [5200, 5250, 5300],
        "GDP (Trillion USD)": [26.9, 27.5, 28.0],
        "Population (Billion)": [0.33, 0.33, 0.33],
        "Energy Use (Mtoe)": [2300, 2350, 2400],
        "HDI": [0.93, 0.94, 0.94],
    })

    editor = pn.widgets.Tabulator(df_input, height=200)

    btn_run = pn.widgets.Button(name="Run Prediction", button_type="success", width=200)
    result_box = pn.pane.Markdown("")

    def run_predict(event):
        edited = editor.value
        result_box.object = (
            "**Prediction executed** (bạn hãy thêm model/GRU ở đây)\n\n"
            "Dữ liệu nhập:\n```text\n"
            f"{edited}\n```"
        )

    btn_run.on_click(run_predict)

    return pn.Column(
        header,
        pn.Row(country_sel, hist_window, year_sel),
        pn.Spacer(height=10),
        pn.pane.Markdown("### Input for Prediction"),
        editor,
        pn.Spacer(height=15),
        pn.Row(pn.Spacer(width=300), btn_run),
        pn.Spacer(height=20),
        result_box,
    )

def recommendation_view():
    header = pn.pane.Markdown("## Recommendation Engine")

    country_sel = pn.widgets.Select(
        name="Country", options=["Vietnam", "Thailand"], value="Vietnam"
    )
    year_sel = pn.widgets.Select(
        name="Year", options=[2026, 2027, 2028], value=2026
    )

    feature_checkbox = pn.widgets.Checkbox(name="GDP", value=True)
    cost_slider = pn.widgets.FloatSlider(
        name="Cost Level", start=0, end=1, step=0.1, value=0.5
    )
    cost_slider.bar_color = "#33cc7a"
    
    btn_run = pn.widgets.Button(name="Run Prediction", button_type="success", width=200)
    result_box = pn.pane.Markdown("")

    def run_recommend(event):
        result_box.object = (
            "**Recommendation executed**\n\n"
            f"- Feature GDP: {feature_checkbox.value}\n"
            f"- Cost Level: {cost_slider.value}"
        )

    btn_run.on_click(run_recommend)

    return pn.Column(
        header,
        pn.Row(country_sel, year_sel),
        pn.Spacer(height=10),
        pn.pane.Markdown("### Adjust Feature Impact"),
        pn.Row(feature_checkbox, cost_slider),
        pn.Spacer(height=15),
        pn.Row(pn.Spacer(width=300), btn_run),
        pn.Spacer(height=20),
        result_box,
    )

# ================== NAV + ROUTER  ==================

location = pn.state.location

def get_page_from_search(search: str) -> str:
    """search dạng '?page=forecast&x=1' hoặc ''."""
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
        return forecast_view()
    elif page == "recommend":
        return recommendation_view()
    else:
        return dashboard_view()

body = pn.bind(router, location.param.search)

# ================== FINAL APP ==================

app = pn.Column(
    title,
    nav,
    pn.Spacer(height=10),
    body,
)

app.servable("CO₂ Emission Dashboard")
