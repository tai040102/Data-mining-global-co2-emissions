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

    # chọn thêm tối đa 2 quốc gia để vẽ chung
    compare_countries = pn.widgets.MultiChoice(
        name="",
        options=countries_by_continent[continents[0]],
        value=[],
        width=220,
        # placeholder="Select up to 2 countries",
    )

        # LIMIT MAX = 2 + KHÔNG CHO TRÙNG COUNTRY CHÍNH
    def on_compare_change(event):
        vals = list(event.new)

        # bỏ country chính nếu user chọn trùng
        vals = [c for c in vals if c != country.value]

        # giới hạn tối đa 2
        if len(vals) > 2:
            vals = vals[:2]

        # chỉ set lại nếu thực sự thay đổi để tránh loop
        if vals != compare_countries.value:
            compare_countries.value = vals

    compare_countries.param.watch(on_compare_change, "value")

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
        opts = countries_by_continent[continent.value]

        # cập nhật LIST cho COUNTRY
        country.options = opts
        if country.value not in opts:
            country.value = opts[0]

        # loại country chính ra khỏi option của compare
        compare_opts = [c for c in opts if c != country.value]

        # cập nhật options
        compare_countries.options = compare_opts

        # đồng thời xóa country chính khỏi value nếu có
        compare_countries.value = [
            c for c in compare_countries.value if c != country.value
        ]

    country.param.watch(lambda e: update_countries(None), "value")

    def filter_block(label, widget):
        return pn.Column(
            pn.pane.HTML(f'<div class="filter-label">{label}</div>'),
            widget,
            width=220,
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
        filter_block("COMPARE (max 2)", compare_countries),
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

    kpi_row = pn.bind(kpi_row_view, country_name=country, period_val=period)

    # ======= CHARTS: COUNTRY + COMPARE =======
    colors_capita = ["#10b981", "#6366f1", "#ef4444"]  # main + 2 compare
    colors_total = ["#065f1f", "#1d4ed8", "#b91c1c"]

    @pn.depends(country, compare_countries, period)
    def chart_capita(country, compare_countries, period):
        y_min, y_max = period
        p = figure(
            height=280,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        all_lines = []
        all_countries = [country] + [c for c in compare_countries if c != country]
        all_countries = all_countries[:3]

        for idx, ctry in enumerate(all_countries):
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
                "Year", "Co2_Capita_tCO2",
                source=src, line_width=3,
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

    @pn.depends(country, compare_countries, period)
    def chart_total(country, compare_countries, period):
        y_min, y_max = period
        p = figure(
            height=280,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        all_lines = []
        all_countries = [country] + [c for c in compare_countries if c != country]
        all_countries = all_countries[:3]

        for idx, ctry in enumerate(all_countries):
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
                "Year", "Co2_MtCO2",
                source=src, line_width=3,
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
            "Year", "Total",
            source=src_global,
            line_width=3,
            color="#0f766e",
            legend_label="Global",
        )
        p.circle("Year", "Total", source=src_global, size=5, color="#0f766e")

        r_cont = p.line(
            "Year", "Total",
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
