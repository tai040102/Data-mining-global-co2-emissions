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

    # COUNTRY: MultiChoice, chọn tối đa 3 country
    first_country = countries_by_continent[continents[0]][0]
    country = pn.widgets.MultiChoice(
        name="",
        options=countries_by_continent[continents[0]],
        value=[first_country],
        width=395,
    )

    # limit max = 3 và unique
    def on_country_change(event):
        vals = list(dict.fromkeys(event.new))  # unique, keep order
        if len(vals) > 3:
            vals = vals[:3]
        if vals != country.value:
            country.value = vals

    country.param.watch(on_country_change, "value")

    # Year range slider
    period = pn.widgets.IntRangeSlider(
        name="",
        start=min(years),
        end=max(years),
        value=(2010, 2020),
        show_value=False,
        sizing_mode="stretch_width",
    )
    period.bar_color = "#33cc7a"

    # period pill
    period_display = pn.bind(
        lambda r: f'<div class="period-pill">{r[0]} → {r[1]}</div>',
        period,
    )

    # update COUNTRY options when continent changes
    def update_countries(event):
        opts = countries_by_continent[continent.value]
        country.options = opts

        # keep only still-valid countries
        new_vals = [c for c in country.value if c in opts]

        # if none left, pick first
        if not new_vals and opts:
            new_vals = [opts[0]]

        # limit to max 3
        new_vals = new_vals[:3]
        if new_vals != country.value:
            country.value = new_vals

    continent.param.watch(update_countries, "value")

    # ======= FILTER LAYOUT =======
    def filter_block(label, widget, width=220):
        return pn.Column(
            pn.pane.HTML(f'<div class="filter-label">{label}</div>'),
            widget,
            width=width,
        )

    # pill + slider in one row so it aligns horizontally
    period_block = pn.Column(
        pn.pane.HTML('<div class="filter-label">PERIOD</div>'),
        pn.Row(
            pn.pane.HTML(period_display, width=140),
            period,
            sizing_mode="stretch_width",
            align="center",
        ),
        width=400,
    )

    filters_row = pn.Row(
        filter_block("CONTINENT", continent, width=230),
        filter_block("COUNTRY (max 3)", country, width=400),
        period_block,
        sizing_mode="stretch_width",
        align="end",
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

    def kpi_row_view(selected_countries, period_val):
        # Show KPI for first selected country
        if not selected_countries:
            return pn.Row()

        main_country = selected_countries[0]
        total, capita, gdp, hdi, energy = compute_kpis(main_country, period_val)
        return pn.Row(
            kpi_card("Total CO₂", total),
            kpi_card("CO₂ per Capita", capita),
            kpi_card("GDP", gdp),
            kpi_card("HDI", hdi),
            kpi_card("Energy per Capita (kWh)", energy),
        )

    kpi_row = pn.bind(kpi_row_view, selected_countries=country, period_val=period)

    # ======= CHARTS: COUNTRY (up to 3) =======
    colors_capita = ["#10b981", "#6366f1", "#ef4444"]  # up to 3
    colors_total = ["#065f1f", "#1d4ed8", "#b91c1c"]

    @pn.depends(country, period)
    def chart_capita(country, period):
        y_min, y_max = period
        p = figure(
            height=280,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        all_lines = []
        selected = (country or [])[:3]

        for idx, ctry in enumerate(selected):
            df = df_all[
                (df_all["Country"] == ctry)
                & (df_all["Year"] >= y_min)
                & (df_all["Year"] <= y_max)
            ].copy()
            if df.empty:
                continue

            df["Country"] = ctry
            src = ColumnDataSource(df[["Year", "Co2_Capita_tCO2", "Country"]])

            color = colors_capita[idx % len(colors_capita)]
            line = p.line(
                "Year",
                "Co2_Capita_tCO2",
                source=src,
                line_width=3,
                color=color,
                legend_label=ctry,
            )
            p.circle("Year", "Co2_Capita_tCO2", source=src, size=6, color=color)
            all_lines.append(line)

        p.xaxis.axis_label = "Year"
        p.yaxis.axis_label = "tCO₂ per capita"

        if all_lines:
            hover = HoverTool(
                tooltips=[
                    ("Country", "@Country"),
                    ("Year", "@Year"),
                    ("CO₂ per capita", "@Co2_Capita_tCO2{0.00000} t"),
                ],
                mode="vline",
                renderers=all_lines,
            )
            p.add_tools(hover)

        p.legend.location = "top_left"
        p.legend.click_policy = "hide"
        return p

    @pn.depends(country, period)
    def chart_total(country, period):
        y_min, y_max = period
        p = figure(
            height=280,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        all_lines = []
        selected = (country or [])[:3]

        for idx, ctry in enumerate(selected):
            df = df_all[
                (df_all["Country"] == ctry)
                & (df_all["Year"] >= y_min)
                & (df_all["Year"] <= y_max)
            ].copy()
            if df.empty:
                continue

            df["Country"] = ctry
            src = ColumnDataSource(df[["Year", "Co2_MtCO2", "Country"]])

            color = colors_total[idx % len(colors_total)]
            line = p.line(
                "Year",
                "Co2_MtCO2",
                source=src,
                line_width=3,
                color=color,
                legend_label=ctry,
            )
            p.circle("Year", "Co2_MtCO2", source=src, size=6, color=color)
            all_lines.append(line)

        p.xaxis.axis_label = "Year"
        p.yaxis.axis_label = "MtCO₂ total"

        if all_lines:
            hover = HoverTool(
                tooltips=[
                    ("Country", "@Country"),
                    ("Year", "@Year"),
                    ("Total CO₂", "@Co2_MtCO2{0,0.00} Mt"),
                ],
                mode="vline",
                renderers=all_lines,
            )
            p.add_tools(hover)

        p.legend.location = "top_left"
        p.legend.click_policy = "hide"
        return p

    charts_row = pn.Row(
        pn.Column("### CO₂ per Capita (Country)", chart_capita),
        pn.Column("### Total CO₂ (Country)", chart_total),
    )

    # ======= GLOBAL vs CONTINENT CHART =======
    @pn.depends(continent, period)
    def chart_global_continent(continent, period):
        y_min, y_max = period

        df_period = df_all[
            (df_all["Year"] >= y_min) & (df_all["Year"] <= y_max)
        ].copy()

        if df_period.empty:
            return figure(
                height=280,
                sizing_mode="stretch_width",
                title="No data for selected period",
            )

        # Global total
        df_global = (
            df_period.groupby("Year", as_index=False)["Co2_MtCO2"].sum()
            .rename(columns={"Co2_MtCO2": "Total"})
        )

        # Continent total
        df_cont = (
            df_period[df_period["Continent"] == continent]
            .groupby("Year", as_index=False)["Co2_MtCO2"].sum()
            .rename(columns={"Co2_MtCO2": "Total"})
        )

        src_global = ColumnDataSource(df_global)
        src_cont = ColumnDataSource(df_cont)

        p = figure(
            height=280,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        r_global = p.line(
            "Year",
            "Total",
            source=src_global,
            line_width=3,
            color="#0f766e",
            legend_label="Global",
        )
        p.circle("Year", "Total", source=src_global, size=5, color="#0f766e")

        r_cont = p.line(
            "Year",
            "Total",
            source=src_cont,
            line_width=3,
            color="#f97316",
            legend_label=continent,
        )
        p.circle("Year", "Total", source=src_cont, size=5, color="#f97316")

        p.xaxis.axis_label = "Year"
        p.yaxis.axis_label = "MtCO₂ total"

        hover = HoverTool(
            tooltips=[
                ("Year", "@Year"),
                ("Total CO₂", "@Total{0,0.00} Mt"),
            ],
            mode="vline",
            renderers=[r_global, r_cont],
        )
        p.add_tools(hover)

        p.legend.location = "top_left"
        p.legend.click_policy = "hide"
        return p

    compare_row = pn.Column(
        "### Global vs Continent Total CO₂",
        chart_global_continent,
    )

    # ======= FINAL LAYOUT =======
    return pn.Column(
        pn.Spacer(height=10),
        filters_row,
        pn.Spacer(height=15),
        kpi_row,
        pn.Spacer(height=20),
        charts_row,
        pn.Spacer(height=20),
        compare_row,
    )
