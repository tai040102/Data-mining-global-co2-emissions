# tab_forecast.py
import panel as pn
import pandas as pd
import requests

API_URL = "http://localhost:8001/predict"

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

    # dataset range (vd 2001–2022)
    min_year = int(min(years))
    max_year = int(max(years))

    country = pn.widgets.Select(
        name="Country",
        options=countries,
        value=countries[0],
        width=300,
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

    # Year không có editor, còn lại là number editor
    editors = {"Year": None}
    editors.update({f: "number" for f in FEATURES})

    editor = pn.widgets.Tabulator(
        df_init,
        height=230,
        show_index=False,
        formatters={"Year": {"type": "plaintext"}},
        editors=editors,
        selectable=False,
    )

    btn_run = pn.widgets.Button(
        name="Run Prediction",
        button_type="default",
        width=220,
    )

    result_box = pn.pane.Markdown("")
    autofill_info = pn.pane.Markdown("", sizing_mode="stretch_width")

    # lưu bản "gốc" từ dataset để lock 2001–2022
    original_df = {"value": df_init.copy()}
    _updating = {"value": False}  # tránh loop watcher

    # ===== helper: style xám cho các dòng bị khóa =====
    def apply_locked_style(df_hist: pd.DataFrame):
        def row_style(row):
            year = row["Year"]
            if min_year <= year <= max_year:
                # tô xám cả dòng
                return ['background-color: #f2f2f2; color: #555555;'] * len(row)
            else:
                return [''] * len(row)

        # gán styler cho tabulator
        editor.style = df_hist.style.apply(row_style, axis=1)

    # ================== HELPER: BUILD HISTORY (CỐ ĐỊNH 5 NĂM) ==================
    def build_history(country_val, predict_year_val):
        """
        Tạo history cố định 5 năm: [Y-5 .. Y-1]
        - Năm trong df_all (2001–2022) -> fill dữ liệu.
        - Năm ngoài range -> để trống feature cho user nhập.
        """
        n = 5

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

        df_hist = build_history(country.value, py)

        # cập nhật bản gốc để dùng khi lock
        original_df["value"] = df_hist.copy()

        # set vào bảng
        _updating["value"] = True
        editor.value = df_hist
        _updating["value"] = False

        # áp style xám cho năm trong dataset
        apply_locked_style(df_hist)

        in_range = (df_hist["Year"] >= min_year) & (df_hist["Year"] <= max_year)
        locked_years = df_hist.loc[in_range, "Year"].tolist()
        editable_years = df_hist.loc[~in_range, "Year"].tolist()

        has_data = (~df_hist[FEATURES].isnull().all(axis=1)).sum()
        n = df_hist.shape[0]

        # msg = (
        #     f"Auto-filled last {n} years. {has_data} year(s) loaded from dataset "
        #     f"({min_year}–{max_year}).\n\n"
        # )
        # if locked_years:
        #     msg += (
        #         f"- 🔒 Locked years (tô xám, dữ liệu lấy từ dataset, không chỉnh được): "
        #         f"**{', '.join(map(str, locked_years))}**\n"
        #     )
        # if editable_years:
        #     msg += (
        #         f"- ✏️ Editable years (ngoài dataset – hãy nhập feature): "
        #         f"**{', '.join(map(str, editable_years))}**\n"
        #     )

        # autofill_info.object = msg

    # ================== WATCHER: CHẶN SỬA NĂM 2001–2022 ==================
    def on_table_change(event):
        if _updating["value"]:
            return

        new_df = event.new
        df_orig = original_df["value"]

        if new_df is None or df_orig is None:
            return
        if len(new_df) != len(df_orig):
            return

        # copy rồi restore lại toàn bộ feature cho các năm nằm trong dataset
        df_fixed = new_df.copy()
        lock_mask = (df_fixed["Year"] >= min_year) & (df_fixed["Year"] <= max_year)

        for f in FEATURES:
            df_fixed.loc[lock_mask, f] = df_orig.loc[lock_mask, f]

        # cập nhật lại vào bảng (cell sẽ nhảy về giá trị gốc => cảm giác bị khóa)
        _updating["value"] = True
        editor.value = df_fixed
        _updating["value"] = False

        # áp lại style xám cho chắc
        apply_locked_style(df_fixed)

    editor.param.watch(on_table_change, "value")

    # watchers cho widgets
    country.param.watch(autofill_table, "value")
    predict_year.param.watch(autofill_table, "value")

    # initial fill
    autofill_table()

    # ================== RUN PREDICTION ==================
    def run_prediction(event):
        df_hist = editor.value
        if df_hist is None or len(df_hist) == 0:
            result_box.object = "⚠️ No input data."
            return

        n_rows = len(df_hist)
        if n_rows != 5:
            missing = 5 - n_rows
            if missing > 0:
                result_box.object = (
                    f"⚠️ History table just have **{n_rows} rows**, "
                    f"needs exactly **5 rows** (5 consecutive years).\n\n"
                    f"👉 Please **add the missing {missing} rows** and fill in all features "
                    "before running the prediction."
                )
            else:
                result_box.object = (
                    f"⚠️ History table has **{n_rows} rows**, but GRU requires **exactly 5 rows**.\n\n"
                    "👉 Please keep exactly 5 consecutive years of history before running the prediction."
                )
            return

        df_hist = df_hist.copy()
        df_orig = original_df["value"]

        # đảm bảo thêm một lần nữa: lock 2001–2022
        lock_mask = (df_hist["Year"] >= min_year) & (df_hist["Year"] <= max_year)
        for f in FEATURES:
            df_hist.loc[lock_mask, f] = df_orig.loc[lock_mask, f]

        # --- FE tự check thiếu ô trống trước khi gọi API ---
        if df_hist[FEATURES].isnull().any().any():
            years_nan = df_hist.loc[df_hist[FEATURES].isnull().any(axis=1), "Year"].tolist()
            year_list = ", ".join(str(int(y)) for y in years_nan)
            result_box.object = (
                f"⚠️ Some feature cells are empty for year(s): **{year_list}**.\n\n"
                "👉 Please fill **all features** for these year(s) before running the prediction."
            )
            return

        payload = {
            "country": country.value,
            "predict_year": int(predict_year.value),
            "model_type": "gru",
            "history": df_hist.to_dict(orient="records"),
        }

        try:
            resp = requests.post(API_URL, json=payload, timeout=10)
        except Exception as e:
            result_box.object = f"❌ API call error: {e}"
            return

        # parse JSON, nếu lỗi thì show raw text để dễ nhìn
        try:
            data = resp.json()
        except Exception as e:
            result_box.object = (
                f"❌ API JSON parse error: {e}\n\n"
                f"Raw response:\n\n```text\n{resp.text}\n```"
            )
            return


        if resp.status_code != 200:
            result_box.object = f"❌ API HTTP {resp.status_code}: {data}"
            return

        if data.get("status") != "ok":
            result_box.object = f"❌ API response: {data.get('message')}"
            return

        pred = data["prediction"]

        result_box.object = (
            f"The model forecasts that **{data['country']}’s** total CO₂ emissions in {data['predict_year']} will be: <span style='color:#147A3C; font-size:16px; font-weight:800;'>**{pred:,.2f} MtCO₂**</span>\n\n"
        )

    btn_run.on_click(run_prediction)

    # ================== LAYOUT ==================
    return pn.Column(
        # pn.pane.Markdown("## Forecast CO₂ Emission"),
        pn.Row(country, predict_year),
        pn.Spacer(height=10),
        pn.pane.Markdown(" <h2 style='color:#147A3C; font-weight:700;'>Input for Prediction</h2>"),
        autofill_info,
        editor,
        pn.Spacer(height=15),
        pn.Row(pn.Spacer(), btn_run, pn.Spacer(), sizing_mode="stretch_width"),
        pn.Spacer(height=10),
        result_box,
    )
