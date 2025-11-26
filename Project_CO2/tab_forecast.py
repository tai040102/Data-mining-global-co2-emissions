# tab_forecast.py
import panel as pn
import pandas as pd
import requests

API_URL = "http://localhost:8000/predict"

FEATURES = [
    "Co2_MtCO2",
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


def create_forecast_view(df_all: pd.DataFrame):

    # ================== WIDGETS ==================
    countries = sorted(df_all["Country"].dropna().unique())
    years = sorted(df_all["Year"].unique())

    country = pn.widgets.Select(
        name="Country",
        options=countries,
        value=countries[0],
        width=300,
    )

    hist_window = pn.widgets.Select(
        name="Historical Data Window",
        options=["Last 3 years", "Last 5 years"],
        value="Last 3 years",
        width=250,
    )

    predict_year = pn.widgets.IntInput(
        name="Predict Year",
        value=int(years[-1]) + 1,
        width=140,
    )

    # ---- table init (sẽ bị autofill ngay sau đó) ----
    last_year = int(years[-1])
    df_init = pd.DataFrame([{
        "Year": last_year,
        "Co2_MtCO2": None,
        "Population": None,
        "GDP": None,
        "Industry_on_GDP": None,
        "Government_Expenditure_on_Education": None,
        "Global_Climate_Risk_Index": None,
        "HDI": None,
        "Renewable_Energy_Percent": None,
        "Deforest_Percent": None,
        "Energy_Capita_kWh": None,
    }])

    editor = pn.widgets.Tabulator(
        df_init,
        height=230,
        show_index=False,
        formatters={"Year": {"type": "plaintext"}},
    )

    btn_run = pn.widgets.Button(
        name="Run Prediction",
        button_type="default",
        width=220,
    )

    result_box = pn.pane.Markdown("")
    autofill_info = pn.pane.Markdown("", sizing_mode="stretch_width")

    # ================== HELPER: BUILD HISTORY ==================
    def build_history(country_val, predict_year_val, hist_window_val):
        """
        Tạo history cố định n năm:
        - Last 3 years: [Y-3, Y-2, Y-1]
        - Last 5 years: [Y-5 .. Y-1]
        Nếu năm nào chưa có trong df_all -> giữ Year, các feature = None.
        """
        n = 3 if "3" in hist_window_val else 5

        df_country = df_all[df_all["Country"] == country_val].copy()
        df_country = df_country.sort_values("Year")
        df_country = df_country[["Year"] + FEATURES]

        target_years = list(range(predict_year_val - n, predict_year_val))

        rows = []
        for y in target_years:
            row = df_country[df_country["Year"] == y]
            if not row.empty:
                rows.append(row.iloc[0].to_dict())
            else:
                blank = {"Year": y}
                for f in FEATURES:
                    blank[f] = None
                rows.append(blank)

        return pd.DataFrame(rows, columns=["Year"] + FEATURES)

    # ================== AUTO-FILL ==================
    def autofill_table(event=None):
        try:
            py = int(predict_year.value)
        except Exception:
            result_box.object = "⚠️ Predict Year is invalid."
            return

        df_hist = build_history(
            country.value,
            py,
            hist_window.value
        )

        editor.value = df_hist

        # đếm số dòng có đủ data (ít nhất 1 feature không null)
        has_data = (~df_hist[FEATURES].isnull().all(axis=1)).sum()
        n = df_hist.shape[0]
        if has_data == 0:
            autofill_info.object = (
                f"Auto-filled {n} years (no historical data found for this period). "
                "All feature cells are empty, please fill them before running prediction."
            )
        else:
            autofill_info.object = (
                f"Auto-filled {n} years. {has_data} year(s) loaded from dataset, "
                f"{n - has_data} year(s) are empty placeholders."
            )

    # watchers
    country.param.watch(autofill_table, "value")
    hist_window.param.watch(autofill_table, "value")
    predict_year.param.watch(autofill_table, "value")

    # initial fill
    autofill_table()

    # ================== RUN PREDICTION ==================
    def run_prediction(event):
        df_hist = editor.value
        if df_hist is None or len(df_hist) == 0:
            result_box.object = "⚠️ No input data."
            return

        if len(df_hist) not in (3, 5):
            result_box.object = f"⚠️ GRU requires **3 or 5 rows**, got {len(df_hist)}."
            return

        # build payload
        payload = {
            "country": country.value,
            "predict_year": int(predict_year.value),
            "model_type": "gru",  # dùng GRU time-series
            "history": df_hist.to_dict(orient="records"),
        }

        try:
            resp = requests.post(API_URL, json=payload, timeout=10)
            data = resp.json()
        except Exception as e:
            result_box.object = f"❌ API error: {e}"
            return

        if resp.status_code != 200:
            result_box.object = f"❌ API HTTP {resp.status_code}: {data}"
            return

        if data.get("status") != "ok":
            # message từ API (VD: thiếu feature, có ô trống, ...)
            result_box.object = f"❌ API response: {data.get('message')}"
            return

        pred = data["prediction"]

        result_box.object = (
            f"### Prediction Result\n"
            f"- **Country**: {data['country']}\n"
            f"- **Predict Year**: {data['predict_year']}\n"
            f"- **Forecast CO₂**: **{pred:,.2f} MtCO₂**"
        )

    btn_run.on_click(run_prediction)

    # ================== LAYOUT ==================
    return pn.Column(
        pn.pane.Markdown("## Forecast CO₂ Emission"),
        pn.Row(country, hist_window, predict_year),
        pn.Spacer(height=10),
        pn.pane.Markdown("### GRU Time-Series Input (Auto-filled)"),
        autofill_info,
        editor,
        pn.Spacer(height=15),
        pn.Row(pn.Spacer(), btn_run, pn.Spacer(), sizing_mode="stretch_width"),
        pn.Spacer(height=10),
        result_box,
    )
