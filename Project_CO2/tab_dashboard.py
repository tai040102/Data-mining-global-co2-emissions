# tab_dashboard.py
import panel as pn
import pandas as pd
from bokeh.plotting import figure
from bokeh.models import HoverTool, ColumnDataSource


def create_dashboard_view(df_all):
    """Return layout for Dashboard tab using df_all dataframe."""

    # ======= prepare data =======
    df_all = df_all.dropna(subset=["Country", "Year", "Co2_MtCO2", "Co2_Capita_tCO2"])
    df_all["Year"] = df_all["Year"].astype(int)

    continents = sorted(df_all["Continent"].dropna().unique())
    countries_by_continent = {
        c: sorted(df_all[df_all["Continent"] == c]["Country"].unique())
        for c in continents
    }
    years = sorted(df_all["Year"].unique())

    # ======= widgets =======
    continent = pn.widgets.Select(
        name="", options=continents, value=continents[0], width=220
    )

    country = pn.widgets.Select(
        name="", options=countries_by_continent[continents[0]], width=220
    )

    period = pn.widgets.IntRangeSlider(
        name="", start=min(years), end=max(years), value=(2010, 2020),
        width=400, show_value=False
    )
    period.bar_color = "#33cc7a"

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

    # ======= KPI helpers =======
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

    def compute_kpis(country_name, year_range):
        y_min, y_max = year_range
        df = df_all[
            (df_all["Country"] == country_name)
            & (df_all["Year"] >= y_min)
            & (df_all["Year"] <= y_max)
        ]

        if df.empty:
            return "0", "0", "0", "0", "0"

        avg_total_co2 = df["Co2_MtCO2"].mean()
        avg_capita_co2 = df["Co2_Capita_tCO2"].mean()
        avg_gdp = df["GDP"].mean() if "GDP" in df else 0
        avg_hdi = df["HDI"].mean() if "HDI" in df else 0
        avg_energy_cap = (
            df["Energy_Capita_kWh"].mean() if "Energy_Capita_kWh" in df else 0
        )

        total_str = f"{avg_total_co2:,.2f} Mt"
        capita_str = f"{avg_capita_co2:.5f} t"
        gdp_str = humanize_gdp(avg_gdp)
        hdi_str = f"{avg_hdi:.3f}"
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

    def kpi_row_view(country_name, period_val):
        total, capita, gdp, hdi, energy = compute_kpis(country_name, period_val)
        return pn.Row(
            kpi_card("Total CO₂", total),
            kpi_card("CO₂ per Capita", capita),
            kpi_card("GDP", gdp),
            kpi_card("HDI", hdi),
            kpi_card("Energy per Capita (kWh)", energy),
        )

    # bind works OK here (tên params khớp)
    kpi_row = pn.bind(kpi_row_view, country_name=country, period_val=period)

    # ======= CHARTS with @pn.depends =======
    @pn.depends(country, period)
    def chart_capita(country, period):
        y_min, y_max = period
        df = df_all[
            (df_all["Country"] == country)
            & (df_all["Year"] >= y_min)
            & (df_all["Year"] <= y_max)
        ].copy()

        source = ColumnDataSource(df[["Year", "Co2_Capita_tCO2"]])

        p = figure(
            height=280,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        p.line("Year", "Co2_Capita_tCO2", source=source, line_width=3, color="#10b981")
        p.circle("Year", "Co2_Capita_tCO2", source=source, size=6, color="#10b981")

        p.xaxis.axis_label = "Year"
        p.yaxis.axis_label = "tCO₂ per capita"

        hover = HoverTool(
            tooltips=[
                ("Year", "@Year"),
                ("CO₂ per capita", "@Co2_Capita_tCO2{0.00000} t"),
            ],
            mode="vline",
        )
        p.add_tools(hover)
        return p

    @pn.depends(country, period)
    def chart_total(country, period):
        y_min, y_max = period
        df = df_all[
            (df_all["Country"] == country)
            & (df_all["Year"] >= y_min)
            & (df_all["Year"] <= y_max)
        ].copy()

        source = ColumnDataSource(df[["Year", "Co2_MtCO2"]])

        p = figure(
            height=280,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        p.line("Year", "Co2_MtCO2", source=source, line_width=3, color="#065f1f")
        p.circle("Year", "Co2_MtCO2", source=source, size=6, color="#065f1f")

        p.xaxis.axis_label = "Year"
        p.yaxis.axis_label = "MtCO₂ total"

        hover = HoverTool(
            tooltips=[
                ("Year", "@Year"),
                ("Total CO₂", "@Co2_MtCO2{0,0.00} Mt"),
            ],
            mode="vline",
        )
        p.add_tools(hover)
        return p

    charts_row = pn.Row(
        pn.Column("### CO₂ per Capita", chart_capita),
        pn.Column("### Total CO₂", chart_total),
    )

    # ======= FINAL LAYOUT =======
    return pn.Column(
        pn.Spacer(height=10),
        filters_row,
        pn.Spacer(height=15),
        kpi_row,
        pn.Spacer(height=20),
        charts_row,
    )
