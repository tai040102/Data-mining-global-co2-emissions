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
        name="Historical Data Window (for GRU)",
        options=["Last 3 years", "Last 5 years"],
        value="Last 3 years",
        width=250,
    )

    predict_year = pn.widgets.IntInput(
        name="Predict Year",
        value=int(years[-1]) + 1,
        width=140,
    )

    model_toggle = pn.widgets.RadioButtonGroup(
        name="Model type",
        options={
            "GRU (time series)": "gru",
            "XGBoost (tabular)": "xgb",
        },
        value="gru",
        button_type="default",          # để CSS tự control màu
        sizing_mode="stretch_width",
    )

    # ---- default row (fallback khi không auto-fill được) ----
    df_init = pd.DataFrame([{
        "Year": int(years[-1]),
        "Co2_MtCO2": 0.0,
        "Population": 0.0,
        "GDP": 0.0,
        "Industry_on_GDP": 0.0,
        "Government_Expenditure_on_Education": 0.0,
        "Global_Climate_Risk_Index": 0.0,
        "HDI": 0.0,
        "Renewable_Energy_Percent": 0.0,
        "Deforest_Percent": 0.0,
        "Energy_Capita_kWh": 0.0,
    }])

    editor = pn.widgets.Tabulator(
        df_init,
        height=230,
        show_index=False,
        formatters={
            "Year": {"type": "plaintext"}
        }
    )

    btn_run = pn.widgets.Button(
        name="Run Prediction",
        button_type="default",
        width=220,
    )

    result_box = pn.pane.Markdown("")
    autofill_info = pn.pane.Markdown("", sizing_mode="stretch_width")

    # ================== HELPER: LẤY LỊCH SỬ TỪ df_all ==================
    def build_history_from_dataset(
        country_val: str,
        predict_year_val: int,
        hist_window_val: str,
        model_type_val: str,
    ):
        df_country = df_all[df_all["Country"] == country_val].copy()
        if df_country.empty:
            return pd.DataFrame()

        df_country = df_country.sort_values("Year")
        df_country = df_country[["Year"] + FEATURES]

        # Nếu model là GRU -----------------------------------------------------------
        if model_type_val == "gru":
            df_past = df_country[df_country["Year"] < predict_year_val]

            # Nếu không có năm nhỏ hơn predict_year → fallback dùng các năm cuối cùng
            if df_past.empty:
                df_past = df_country

            n = 3 if "3" in hist_window_val else 5
            return df_past.tail(n).reset_index(drop=True)

        # Nếu model là XGBoost -------------------------------------------------------
        else:
            # Nếu năm dự đoán CÓ trong dataset → load đúng năm đó
            df_exact = df_country[df_country["Year"] == predict_year_val]
            if not df_exact.empty:
                return df_exact.reset_index(drop=True)

            # Nếu năm dự đoán không có trong dataset → user sẽ nhập thủ công
            return pd.DataFrame()   # IMPORTANT: return empty → giữ nguyên bảng editor

    # ================== AUTO-FILL BẢNG KHI ĐỔI PARAM ==================
    def autofill_table(event=None):
        model_type = model_toggle.value

        df_hist = build_history_from_dataset(
            country_val=country.value,
            predict_year_val=int(predict_year.value),
            hist_window_val=hist_window.value,
            model_type_val=model_type,
        )

        # ===== GRU: dùng lịch sử 3 hoặc 5 năm =====
        if model_type == "gru":
            if df_hist.empty:
                # không có ANY data cho country này -> tạo n dòng trống
                n = 3 if "3" in hist_window.value else 5
                template = pd.DataFrame([df_init.iloc[0]] * n)
                # Year cho các dòng trống = predict_year - i (cho đẹp), không bắt buộc
                base_year = int(predict_year.value) - n
                template["Year"] = [base_year + i for i in range(n)]
                editor.value = template
                autofill_info.object = (
                    "⚠️ No GRU history found. Using blank rows, please fill manually."
                )
            else:
                # chỉ giữ đúng những năm có trong data
                editor.value = df_hist
                autofill_info.object = f"Auto-filled {len(df_hist)} years for GRU."
            return  # kết thúc GRU branch

        # ===== XGBoost: 1 row, nếu không có data thì reset bảng về 1 dòng trống =====
        if model_type == "xgb":
            if df_hist.empty:
                # predict_year không có trong dataset -> reset về 1 row trống
                template = df_init.copy()
                template.loc[0, "Year"] = int(predict_year.value)
                # các feature khác để 0.0 để bạn nhập tay
                editor.value = template
                autofill_info.object = (
                    "Year not found in dataset. Table reset to a single empty row "
                    "for XGBoost. Please enter features manually."
                )
            else:
                # có đúng 1 row cho năm đó trong data
                editor.value = df_hist
                autofill_info.object = (
                    f"Auto-filled row for XGBoost (Year = {int(df_hist['Year'].iloc[0])})."
                )

    # attach watchers
    country.param.watch(autofill_table, "value")
    hist_window.param.watch(autofill_table, "value")
    predict_year.param.watch(autofill_table, "value")
    model_toggle.param.watch(autofill_table, "value")

    # Khởi tạo lần đầu
    autofill_table()

    # ================== CALLBACK PREDICTION ==================
    def run_prediction(event):
        df_hist = editor.value

        if df_hist is None or len(df_hist) == 0:
            result_box.object = "⚠️ Please enter or auto-fill some input data."
            return

        model_type = model_toggle.value
        n_rows = len(df_hist)

        if model_type == "gru" and n_rows not in (3, 5):
            result_box.object = (
                f"⚠️ GRU requires **3 or 5 rows** of history, got {n_rows}."
            )
            return

        payload = {
            "country": country.value,
            "predict_year": int(predict_year.value),
            "model_type": model_type,  # 'gru' or 'xgb'
            "history": df_hist.to_dict(orient="records"),
        }

        try:
            resp = requests.post(API_URL, json=payload, timeout=10)
            data = resp.json()
        except Exception as e:
            result_box.object = f"❌ Error calling API: `{e}`"
            return

        if data.get("status") != "ok":
            result_box.object = f"❌ API error: `{data.get('message')}`"
            return

        pred = data["prediction"]
        model_used = data["model"]

        result_box.object = (
            f"### Prediction result\n"
            f"- **Country**: {data['country']}\n"
            f"- **Model**: {model_used}\n"
            f"- **Predict year**: {data['predict_year']}\n"
            f"- **Forecast CO₂**: **{pred:,.2f} MtCO₂**"
        )

    btn_run.on_click(run_prediction)

    # ================== LAYOUT ==================
    header = pn.pane.Markdown("## Forecast CO₂ Emission", sizing_mode="stretch_width")

    info_text = pn.pane.Markdown(
        "- **GRU (time series)** → uses the last **3 or 5 years** as history.\n"
        "- **XGBoost (tabular)** → only needs **one row** of features (selected year).\n",
        sizing_mode="stretch_width",
    )

    return pn.Column(
        header,
        pn.Row(country, hist_window, predict_year),
        pn.Spacer(height=10),
        model_toggle,
        pn.Spacer(height=10),
        pn.pane.Markdown("### Input for Prediction"),
        info_text,
        autofill_info,
        editor,
        pn.Spacer(height=10),
        pn.Row(
            pn.Spacer(),
            btn_run,
            pn.Spacer(),
            sizing_mode="stretch_width"
        ),
        pn.Spacer(height=10),
        result_box,
    )
