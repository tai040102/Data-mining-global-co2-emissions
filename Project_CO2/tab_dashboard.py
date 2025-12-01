import panel as pn
import pandas as pd
from math import pi

from bokeh.plotting import figure
from bokeh.models import HoverTool, ColumnDataSource


def create_dashboard_view(df_all):
    """Return layout for Dashboard tab using df_all dataframe."""

    # ======= prepare data =======
    df_all = df_all.dropna(subset=["Country", "Year", "Co2_MtCO2", "Co2_Capita_tCO2"])
    df_all["Year"] = df_all["Year"].astype(int)

    # continents & countries
    base_continents = sorted(df_all["Continent"].dropna().unique())
    countries_by_continent = {
        c: sorted(df_all[df_all["Continent"] == c]["Country"].unique())
        for c in base_continents
    }

    # thêm Global
    all_countries = sorted(df_all["Country"].unique())
    countries_by_continent["Global"] = all_countries
    continents = ["Global"] + base_continents

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
        width=420,
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
        start=int(min(years)),
        end=int(max(years)),
        value=(2010, 2020),
        show_value=False,
        sizing_mode="stretch_width",
    )
    period.bar_color = "#33cc7a"

    # period pill
    period_display = pn.bind(
        lambda r: f'<div class="period-pill">{int(r[0])} → {int(r[1])}</div>',
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
        width=420,
    )

    filters_row = pn.Row(
        filter_block("CONTINENT", continent, width=230),
        filter_block("COUNTRY (max 3)", country, width=420),
        period_block,
        sizing_mode="stretch_width",
        align="end",
        margin=(0, 0, 10, 0),
    )

    # ========= COMMON SCOPE HELPER (GLOBAL / MULTI-COUNTRY) =========
    def get_scope_df(cont_val, countries_val, year_range):
        y_min, y_max = year_range
        base = df_all[
            (df_all["Year"] >= y_min) & (df_all["Year"] <= y_max)
        ].copy()

        if cont_val == "Global":
            return base

        selected = list(countries_val or [])
        if selected:
            return base[base["Country"].isin(selected)]

        # fallback: theo continent nếu chẳng may không có country
        return base[base["Continent"] == cont_val]

    # ======= KPI helpers =======

    COL_POP = "Population"
    COL_GOV_EDU = "Government_Expenditure_on_Education"
    COL_CRI = "Global_Climate_Risk_Index"
    COL_AREA = "Area_ha"
    COL_ENERGY_CAPITA = "Energy_Capita_kWh"
    COL_DEFOREST = "Deforest_Area_ha"
    COL_FOREST = "Forest_Area_ha"

    def _safe_mean(df, col):
        if col in df and not df[col].dropna().empty:
            return df[col].mean()
        return None

    def _safe_sum(df, col):
        if col in df and not df[col].dropna().empty:
            return df[col].sum()
        return None

    def _fmt_number(x, unit=""):
        if x is None or pd.isna(x):
            return "N/A"
        if x >= 1e12:
            return f"{x/1e12:.2f} T{unit}"
        if x >= 1e9:
            return f"{x/1e9:.2f} B{unit}"
        if x >= 1e6:
            return f"{x/1e6:.2f} M{unit}"
        return f"{x:,.2f}{unit}"

    def compute_kpis_from_df(df_scope: pd.DataFrame):
        kpis = {}
        if df_scope.empty:
            return kpis

        # --- Existing KPIs ---
        kpis["Total CO₂"] = f"{df_scope['Co2_MtCO2'].mean():,.2f} Mt"
        kpis["CO₂ per Capita"] = f"{df_scope['Co2_Capita_tCO2'].mean():.5f} t"
        if "GDP" in df_scope:
            kpis["GDP"] = _fmt_number(df_scope["GDP"].mean())
        if "HDI" in df_scope:
            kpis["HDI"] = f"{df_scope['HDI'].mean():.3f}"
        if COL_POP in df_scope:
            kpis["Population"] = _fmt_number(df_scope[COL_POP].mean())

        # --- Government Expenditure on Education ---
        gov_edu = _safe_mean(df_scope, COL_GOV_EDU)
        if gov_edu is not None:
            kpis["Government Expenditure on Education"] = f"{gov_edu:.2f}%"

        # ======================
        # NEW KPI 1: Total Energy (MWh)
        # ======================
        if "Energy_Total_MWh" in df_scope.columns:
            total_energy = _safe_mean(df_scope, "Energy_Total_MWh")
        else:
            # nếu không có Energy_Total_MWh → tính từ: Pop × Energy_per_capita
            pop = _safe_mean(df_scope, COL_POP)
            ecap = _safe_mean(df_scope, COL_ENERGY_CAPITA)
            total_energy = (pop * ecap / 1000) if pop and ecap else None

        if total_energy:
            kpis["Total Energy (MWh)"] = _fmt_number(total_energy, "")

        # ======================
        # NEW KPI 2: Total Area (Ha)
        # ======================
        total_area = _safe_mean(df_scope, COL_AREA)
        if total_area:
            kpis["Total Area (Ha)"] = _fmt_number(total_area, "")

        # ======================
        # Keep CRI (Important)
        # ======================
        cri = _safe_mean(df_scope, COL_CRI)
        if cri is not None:
            kpis["Global Climate Risk Index"] = f"{cri:.1f}"

        return kpis

    def kpi_card(label, value, width=230):
        html = f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """
        return pn.pane.HTML(html, height=90, width=width)

    # ORDER (UPDATED)
    def kpi_row_view(selected_countries, period_val, continent_val):
        df_scope = get_scope_df(continent_val, selected_countries, period_val)
        kpis = compute_kpis_from_df(df_scope)
        if not kpis:
            return pn.Column()

        primary = [
            "Total CO₂",
            "CO₂ per Capita",
            "Population",
            "GDP",
            "Government Expenditure on Education",
        ]

        secondary = [
            "Total Energy (MWh)",
            "Total Area (Ha)",
            "Global Climate Risk Index",
            "HDI",
        ]

        row1 = [kpi_card(k, kpis[k]) for k in primary if k in kpis]
        row2 = [kpi_card(k, kpis[k]) for k in secondary if k in kpis]

        return pn.Column(
            pn.Row(*row1, sizing_mode="fixed", margin=(0, 0, 10, 0)),
            pn.Row(*row2, sizing_mode="fixed"),
        )

    kpi_row = pn.bind(
        kpi_row_view,
        selected_countries=country,
        period_val=period,
        continent_val=continent,
    )

    # ======= PIE CHART HELPERS =======
    # ======= PIE CHART HELPERS =======
    def make_pie_figure(title, data_dict):
        if not data_dict:
            data_dict = {"N/A": 1.0}

        labels = list(data_dict.keys())
        values = []
        for v in data_dict.values():
            try:
                values.append(max(float(v), 0))
            except Exception:
                values.append(0.0)

        total = sum(values)
        if total == 0:
            values = [1.0 for _ in values]
            total = float(len(values))

        # chuyển sang %
        percents = [(v / total) * 100 for v in values]

        # ép lát quá nhỏ cho dễ nhìn (min 3%)
        min_share = 3.0
        if any(p > 0 for p in percents):
            adj = []
            for p in percents:
                adj.append(max(p, min_share) if p > 0 else 0.0)
            total_adj = sum(adj)
            percents = [(p / total_adj) * 100 for p in adj]

        # tính góc
        angles = [p / 100 * 2 * pi for p in percents]
        start_angles, end_angles = [], []
        cur = 0
        for a in angles:
            start_angles.append(cur)
            cur += a
            end_angles.append(cur)

        colors = ["#22c55e", "#a7f3d0", "#16a34a", "#bbf7d0"][: len(labels)]

        src = ColumnDataSource(
            data=dict(
                start_angle=start_angles,
                end_angle=end_angles,
                value=percents,
                label=labels,
                color=colors,
            )
        )

        # chỉ vẽ pie, KHÔNG dùng legend của Bokeh nữa
        p = figure(
            height=280,
            width=340,
            title=title,
            toolbar_location=None,
            tools="hover",
            tooltips="@label: @value{0.0}%",
            match_aspect=True,
        )

        p.wedge(
            x=0,
            y=0.15,           # đẩy pie lên một chút
            radius=0.55,
            start_angle="start_angle",
            end_angle="end_angle",
            line_color="white",
            fill_color="color",
            source=src,
        )

        p.axis.visible = False
        p.grid.visible = False
        p.outline_line_color = None

        # ==== legend tự build bằng HTML đặt DƯỚI figure ====
        legend_items = []
        for lbl, col in zip(labels, colors):
            legend_items.append(
                f"""
                <span class="pie-legend-item">
                    <span class="pie-legend-color" style="background:{col};"></span>
                    <span class="pie-legend-label">{lbl}</span>
                </span>
                """
            )
        legend_html = (
            '<div class="pie-legend">'
            + "".join(legend_items)
            + "</div>"
        )

        legend_pane = pn.pane.HTML(legend_html, height=30)

        # trả về 1 Column: pie + legend
        return pn.Column(p, legend_pane)

    # ======= PIE: GDP Allocation by Sector (Industry vs Others) =======
    @pn.depends(continent, country, period)
    def pie_gdp(continent, country, period):
        df_scope = get_scope_df(continent, country, period)
        if df_scope.empty:
            return make_pie_figure("GDP Allocation by Sector", {"N/A": 1})

        ind = df_scope["Industry_on_GDP"].mean() if "Industry_on_GDP" in df_scope else 0.0
        ind = max(min(ind, 100.0), 0.0)
        others = max(100.0 - ind, 0.0)

        data = {"Industry": ind, "Others": others}
        return make_pie_figure("GDP Allocation by Sector", data)

    # ======= PIE: Energy Sources (Renewable vs Non-renewable) =======
    @pn.depends(continent, country, period)
    def pie_energy(continent, country, period):
        df_scope = get_scope_df(continent, country, period)
        if df_scope.empty:
            return make_pie_figure("Distribution of Energy Sources", {"N/A": 1})

        ren = df_scope["Renewable_Energy_Percent"].mean() if "Renewable_Energy_Percent" in df_scope else 0.0
        ren = max(min(ren, 100.0), 0.0)
        non_ren = max(100.0 - ren, 0.0)

        data = {"Renewable": ren, "Non-renewable": non_ren}
        return make_pie_figure("Distribution of Energy Sources", data)

    # ======= PIE: Land Area (Deforest, Forest, Total Area) =======
    @pn.depends(continent, country, period)
    def pie_land(continent, country, period):
        df_scope = get_scope_df(continent, country, period)
        if df_scope.empty:
            return make_pie_figure("Distribution of Total Land Area", {"N/A": 1})

        deforest = df_scope["Deforest_Area_ha"].sum() if "Deforest_Area_ha" in df_scope else 0
        forest   = df_scope["Forest_Area_ha"].sum() if "Forest_Area_ha" in df_scope else 0
        total    = df_scope["Area_ha"].sum() if "Area_ha" in df_scope else 0

        def safe(x):
            if x is None or pd.isna(x):
                return 0.0
            return max(float(x), 0.0)

        deforest = safe(deforest)
        forest   = safe(forest)
        total    = safe(total)

        data = {
            "Deforested": deforest,
            "Forest": forest,
            "Total Area": total,
        }
        return make_pie_figure("Distribution of Total Land Area", data)

    pie_row = pn.Row(
        pie_gdp,
        pie_energy,
        pie_land,
        sizing_mode="stretch_width",
        margin=(0, 0, 10, 0),
    )

    # ======= LINE CHARTS: COUNTRY / GLOBAL =======
    colors_capita = ["#10b981", "#6366f1", "#ef4444"]  # up to 3
    colors_total = ["#065f1f", "#1d4ed8", "#b91c1c"]

    @pn.depends(continent, country, period)
    def chart_capita(continent, country, period):
        y_min, y_max = period
        p = figure(
            height=280,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        if continent == "Global":
            df_sel = df_all[
                (df_all["Year"] >= y_min) & (df_all["Year"] <= y_max)
            ]
            if df_sel.empty:
                return p
            # trung bình toàn cầu theo năm
            df_global = (
                df_sel.groupby("Year", as_index=False)["Co2_Capita_tCO2"]
                .mean()
                .rename(columns={"Co2_Capita_tCO2": "Capita"})
            )
            df_global["Label"] = "Global"

            src = ColumnDataSource(df_global)
            line = p.line(
                "Year",
                "Capita",
                source=src,
                line_width=3,
                color="#10b981",
                legend_label="Global",
            )
            p.circle("Year", "Capita", source=src, size=6, color="#10b981")

            hover = HoverTool(
                tooltips=[
                    ("Label", "@Label"),
                    ("Year", "@Year"),
                    ("CO₂ per capita", "@Capita{0.00000} t"),
                ],
                mode="vline",
                renderers=[line],
            )
            p.add_tools(hover)
        else:
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

        p.xaxis.axis_label = "Year"
        p.yaxis.axis_label = "tCO₂ per capita"
        p.legend.location = "top_left"
        p.legend.click_policy = "hide"
        return p

    @pn.depends(continent, country, period)
    def chart_total(continent, country, period):
        y_min, y_max = period
        p = figure(
            height=280,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        if continent == "Global":
            df_sel = df_all[
                (df_all["Year"] >= y_min) & (df_all["Year"] <= y_max)
            ]
            if df_sel.empty:
                return p
            df_global = (
                df_sel.groupby("Year", as_index=False)["Co2_MtCO2"]
                .sum()
                .rename(columns={"Co2_MtCO2": "Total"})
            )
            df_global["Label"] = "Global"

            src = ColumnDataSource(df_global)
            line = p.line(
                "Year",
                "Total",
                source=src,
                line_width=3,
                color="#065f1f",
                legend_label="Global",
            )
            p.circle("Year", "Total", source=src, size=6, color="#065f1f")

            hover = HoverTool(
                tooltips=[
                    ("Label", "@Label"),
                    ("Year", "@Year"),
                    ("Total CO₂", "@Total{0,0.00} Mt"),
                ],
                mode="vline",
                renderers=[line],
            )
            p.add_tools(hover)
        else:
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

        p.xaxis.axis_label = "Year"
        p.yaxis.axis_label = "MtCO₂ total"
        p.legend.location = "top_left"
        p.legend.click_policy = "hide"
        return p

    charts_row = pn.Row(
        pn.Column("### CO₂ Emission Trend by Year", chart_total, sizing_mode="stretch_width"),
        pn.Column("### CO₂ Emission per Capita Trend by Year", chart_capita, sizing_mode="stretch_width"),
        sizing_mode="stretch_width",
    )

    # ======= FINAL LAYOUT =======
    return pn.Column(
        pn.Spacer(height=10),
        filters_row,
        pn.Spacer(height=5),
        kpi_row,
        pn.Spacer(height=10),
        pie_row,
        pn.Spacer(height=10),
        charts_row,
    )
