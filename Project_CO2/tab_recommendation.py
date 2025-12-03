# tab_recommendation.py
import panel as pn
import pandas as pd

FEATURES = [
    "Population",
    "GDP",
    "Industry_on_GDP",
    "Government_Expenditure_on_Education",
    "Global_Climate_Risk_Index",
    "HDI",
    "Renewable_Energy_Percent",
    "Deforest_Percent",
    "Energy_Capita_kWh",
]


def _pretty_name(feat: str) -> str:
    return feat.replace("_", " ")


def _fmt_value(v) -> str:
    """Format số cho đẹp: lớn thì không thập phân, nhỏ thì 2 chữ số."""
    if v is None:
        return "0"
    try:
        v = float(v)
    except Exception:
        return str(v)
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    else:
        return f"{v:,.2f}"


def create_recommendation_view(df_all: pd.DataFrame):

    # ========== PREPARE DATA ==========
    df_all = df_all.copy()
    df_all = df_all.dropna(subset=["Country", "Year"])
    df_all["Year"] = df_all["Year"].astype(int)

    base_years = sorted(df_all["Year"].unique())
    min_base_year = min(base_years)
    max_base_year = max(base_years)

    # Year dùng cho UI: từ (min+1) tới (max+1) -> VD 2002..2023
    ui_years = list(range(min_base_year + 1, max_base_year + 2))

    countries = sorted(df_all["Country"].unique())

    # ========== TOP CONTROLS ==========
    header = pn.pane.Markdown(
        "## Recommendation Engine",
        css_classes=["rec-header"],
    )

    country_sel = pn.widgets.Select(
        name="Country",
        options=countries,
        value="Vietnam" if "Vietnam" in countries else countries[0],
        css_classes=["rec-select"],
    )

    year_sel = pn.widgets.Select(
        name="Year",
        options=ui_years,
        value=max(ui_years),
        css_classes=["rec-select"],
    )

    co2_target = pn.widgets.FloatInput(
        name="CO₂ Emission Target (MtCO₂)",
        value=100,
        step=10,
        css_classes=["rec-target-input"],
    )

    top_row = pn.Row(
        pn.Column(
            pn.pane.Markdown("**Country**", margin=(0, 0, 2, 0)),
            country_sel,
        ),
        pn.Spacer(width=30),
        pn.Column(
            pn.pane.Markdown("**Year**", margin=(0, 0, 2, 0)),
            year_sel,
        ),
        pn.Spacer(width=30),
        pn.Column(
            pn.pane.Markdown("🎯 **CO₂ Emission Target**", margin=(0, 0, 2, 0)),
            co2_target,
        ),
        sizing_mode="stretch_width",
        css_classes=["rec-top-row"],
    )

    # ========== TABLE HEADER (1 row) ==========

    header_prev = pn.pane.Markdown("**Data (Year-1)**", css_classes=["rec-data-cell"])
    header_curr = pn.pane.Markdown("**Data (Year)**", css_classes=["rec-data-cell"])

    header_row = pn.Row(
        pn.Spacer(),  # checkbox
        pn.pane.Markdown("**Feature**", css_classes=["rec-feature-name"]),
        header_prev,
        pn.pane.Markdown("**Max reduction rate**"),
        pn.pane.Markdown("**Max increase rate**"),
        header_curr,
        css_classes=["rec-row", "rec-row-header"],
        sizing_mode="stretch_width",
    )

    # ========== TABLE BODY (1 row / feature) ==========

    feature_controls = []
    body_rows = []

    for feat in FEATURES:
        cb = pn.widgets.Checkbox(value=False)

        data_prev = pn.pane.Markdown(
            "0",
            css_classes=["rec-data-cell"],
        )

        max_reduce = pn.widgets.FloatSlider(
            name="",
            start=-100,
            end=0,
            value=-10,
            step=1,
            bar_color="#ef4444",
        )

        max_increase = pn.widgets.FloatSlider(
            name="",
            start=0,
            end=100,
            value=10,
            step=1,
            bar_color="#22c55e",
        )

        # cột Data (Year) dùng input HTML để không phá layout
        data_curr = pn.pane.HTML(
            '<input type="number" class="rec-num-input" value="0" />',
            css_classes=["rec-data-curr"],
        )

        feature_controls.append(
            dict(
                name=feat,
                checkbox=cb,
                data_prev=data_prev,
                max_reduce=max_reduce,
                max_increase=max_increase,
                data_curr=data_curr,
            )
        )

        row = pn.Row(
            cb,
            pn.pane.Markdown(
                _pretty_name(feat),
                css_classes=["rec-feature-name"],
            ),
            data_prev,
            max_reduce,
            max_increase,
            data_curr,
            css_classes=["rec-row"],
            sizing_mode="stretch_width",
        )
        body_rows.append(row)

    table = pn.Column(
        header_row,
        *body_rows,
        css_classes=["rec-table"],
        sizing_mode="stretch_width",
    )

    # ========== UPDATE DATA THEO COUNTRY & YEAR ==========
    def update_feature_values(event=None):
        ui_year = int(year_sel.value)

        # Label hiển thị đúng
        header_prev.object = f"**Data {ui_year - 1}**"
        header_curr.object = f"**Data {ui_year}**"

        prev_year = ui_year - 1
        curr_year = ui_year

        df_country = df_all[df_all["Country"] == country_sel.value]

        row_prev = df_country[df_country["Year"] == prev_year]
        row_curr = df_country[df_country["Year"] == curr_year]

        for fc in feature_controls:
            col = fc["name"]

            # -------- Data (Year-1): chỉ hiển thị --------
            if not row_prev.empty and col in row_prev.columns:
                v_prev = row_prev.iloc[0][col]
            else:
                v_prev = 0
            v_prev = 0 if pd.isna(v_prev) else v_prev
            fc["data_prev"].object = _fmt_value(v_prev)

            # -------- Data (Year): nếu không có dữ liệu -> 0 --------
            if not row_curr.empty and col in row_curr.columns:
                v_curr = row_curr.iloc[0][col]
                v_curr = 0 if pd.isna(v_curr) else v_curr
            else:
                v_curr = 0

            # giá trị đưa vào thuộc tính value của input -> KHÔNG format comma
            try:
                raw_val = float(v_curr)
            except Exception:
                raw_val = 0.0

            fc["data_curr"].object = (
                f'<input type="number" class="rec-num-input" value="{raw_val}" />'
            )

    country_sel.param.watch(update_feature_values, "value")
    year_sel.param.watch(update_feature_values, "value")
    update_feature_values()

    # ========== RECOMMEND BUTTON ==========
    btn_recommend = pn.widgets.Button(
        name="Recommend",
        button_type="default",
        width=230,
        css_classes=["run-btn", "rec-recommend-btn"],
    )

    recommend_text = pn.pane.Markdown(
        "",
        css_classes=["rec-result-text"],
    )

    def run_recommend(event):
        target = co2_target.value
        selected = [fc for fc in feature_controls if fc["checkbox"].value]

        if not selected:
            recommend_text.object = (
                "Please select at least **one feature** to adjust."
            )
            return

        lines = [
            f"To achieve a CO₂ emission level of <span style='color:#147a3c; font-weight:700'>{target:.0f} MtCO₂</span>,",
            "the model indicates that the following features need to be adjusted:",
        ]
        for fc in selected:
            name = _pretty_name(fc["name"])
            dec = fc["max_reduce"].value
            inc = fc["max_increase"].value
            red = f"<span style='color:#ef4444'>{dec:.0f}%</span>"
            green = f"<span style='color:#22c55e'>+{inc:.0f}%</span>"

            lines.append(
                f"- **{name}**: between {red} reduction and {green} increase"
            )


        recommend_text.object = "\n".join(lines)

    btn_recommend.on_click(run_recommend)

    recommend_block = pn.Column(
        pn.Row(pn.Spacer(), btn_recommend, pn.Spacer(), sizing_mode="stretch_width"),
        pn.Spacer(height=15),
        recommend_text,
        css_classes=["rec-recommend-block"],
    )

    # ========== RIGHT CARD: PREDICT CO2 ==========
    predict_inputs = {
        feat: pn.widgets.FloatInput(
            name=_pretty_name(feat),
            value=0.0,
            step=1,
            css_classes=["rec-predict-input"],
        )
        for feat in FEATURES
    }

    btn_predict = pn.widgets.Button(
        name="Predict",
        button_type="success",
        width=220,
        css_classes=["run-btn", "rec-predict-btn"],
    )

    predict_result = pn.pane.Markdown(
        "",
        align="center",
        css_classes=["rec-predict-result"],
    )

    def run_predict(event):
        total = sum(widget.value for widget in predict_inputs.values())

        predict_result.object = (
            "The predicted total CO₂ emissions is:<br><br>"
            f"<span style='color:#147a3c; font-size:22px; font-weight:700'>{total/100:.1f} MtCO₂</span>"
        )

    btn_predict.on_click(run_predict)

    predict_card = pn.Card(
        pn.Column(
            *predict_inputs.values(),
            pn.Spacer(height=15),
            pn.Row(pn.Spacer(), btn_predict, pn.Spacer()),
            pn.Spacer(height=10),
            predict_result,
        ),
        title="Predict CO₂ Emissions",
        collapsible=False,
        css_classes=["rec-predict-card"],
        sizing_mode="fixed",
        width=330,
    )

    # ========== FINAL LAYOUT ==========
    left_panel = pn.Column(
        header,
        pn.Spacer(height=5),
        top_row,
        pn.Spacer(height=10),
        table,
        pn.Spacer(height=10),
        recommend_block,
        sizing_mode="stretch_width",
        css_classes=["rec-left-panel"],
        width=900,
    )

    layout = pn.Row(
        left_panel,
        pn.Spacer(width=20),
        predict_card,
        sizing_mode="stretch_width",
        css_classes=["rec-main-row"],
    )

    return layout
