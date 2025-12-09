# tab_recommendation.py
import panel as pn
import pandas as pd
import requests
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
API_URL = "http://localhost:8003/recommend_v2"

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



    # Year dùng cho UI: từ (min+1) tới (max+1) -> VD 2002..2023
    

    countries = sorted(df_all["Country"].unique())

    # ========== TOP CONTROLS ==========
    header = pn.pane.Markdown(
        "## Recommendation Engine",
        css_classes=["rec-header"],
    )

    country_sel = pn.widgets.Select(
        name="Country",
        options=countries,
        value="Viet Nam" if "Viet Nam" in countries else countries[0],
        css_classes=["rec-select"],
    )

    year_sel = pn.widgets.Select(
        name="Year",
        options=[2023],  
        value=2023,      
        disabled=True,   
        css_classes=["rec-select"],
    )

    co2_target = pn.widgets.FloatInput(
        name="CO₂ Emission Target (MtCO₂)",
        placeholder = "Example: 100",
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
            pn.pane.Markdown("**CO₂ Emission Target**", margin=(0, 0, 2, 0)),
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
        cb = pn.widgets.Checkbox(value=False, align='center', margin=(0, 5, 0, 5))
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
            disabled=True, #update
        )

        max_increase = pn.widgets.FloatSlider(
            name="",
            start=0,
            end=100,
            value=10,
            step=1,
            bar_color="#22c55e",
            disabled=True, #update
        )

        # cột Data (Year) dùng input HTML để không phá layout
        data_curr = pn.widgets.FloatInput(
            value=0.0,
            step=0.01,
            # hide-spinner: ẩn mũi tên, minimal-input: bỏ khung viền
            css_classes=["hide-spinner", "minimal-input"], 
            sizing_mode="stretch_width",
            height=30,
            margin=(0, 10, 0, 0)
        )
        
        def toggle_row(event, mr=max_reduce, mi=max_increase, dc=data_curr, dp=data_prev):
            is_checked = event.new
            
            mr.disabled = not is_checked
            mi.disabled = not is_checked
            
            if is_checked:
                # Nếu Tick (Chạy tối ưu): Ẩn ô nhập Data 2023 đi
                dc.visible = False
            else:
                # Nếu Bỏ Tick (Cố định): Hiện ô nhập lên cho người dùng sửa
                dc.visible = True
                
                # Logic phụ: Nếu user chưa nhập gì (hoặc = 0), tự động lấy giá trị từ cột bên trái đổ sang
                if dc.value == 0:
                    try:
                        # Parse giá trị từ data_prev (vd: "40.578")
                        val_str = dp.object.replace(".", "").replace(",", ".")
                        dc.value = float(val_str)
                    except:
                        pass

        cb.param.watch(toggle_row, 'value')

        feature_controls.append(
            dict(name=feat, checkbox=cb, data_prev=data_prev, max_reduce=max_reduce, max_increase=max_increase, data_curr=data_curr)
        )

        row = pn.Row(
            cb,
            pn.pane.Markdown(_pretty_name(feat), css_classes=["rec-feature-name"]),
            data_prev, max_reduce, max_increase, data_curr,
            css_classes=["rec-row"], sizing_mode="stretch_width",
        )
        body_rows.append(row)

    table = pn.Column(header_row, *body_rows, css_classes=["rec-table"], sizing_mode="stretch_width")

    # ========== UPDATE DATA THEO COUNTRY & YEAR ==========
    def update_feature_values(event=None):
        ui_year = int(year_sel.value)

        header_prev.object = f"**Data {ui_year - 1}**"
        header_curr.object = f"**Data {ui_year}**"

        prev_year = ui_year - 1
        df_country = df_all[df_all["Country"] == country_sel.value]
        row_prev = df_country[df_country["Year"] == prev_year]
        
        for fc in feature_controls:
            col = fc["name"]
            is_checked = fc["checkbox"].value

            # 1. Lấy dữ liệu thô từ DataFrame
            val_prev = 0
            if not row_prev.empty and col in row_prev.columns:
                val_prev = row_prev.iloc[0][col]
            
            val_prev = 0 if pd.isna(val_prev) else val_prev
            
  

            val_prev = round(float(val_prev), 2)

            # 2. Cập nhật cột Data 2022 (Text hiển thị)
    
            fc["data_prev"].object = _fmt_value(val_prev)

            # 3. Cập nhật cột Data 2023 (Ô nhập liệu)
            fc["data_curr"].value = val_prev
            
            # Logic ẩn hiện ô nhập liệu
            fc["data_curr"].visible = not is_checked

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
    predict_inputs = {
        feat: pn.widgets.FloatInput(
            name=_pretty_name(feat), value=0.0, step=1, start=0, 
            css_classes=["rec-predict-input", "hide-spinner"]
        ) for feat in FEATURES
    }
    def run_recommend(event):
        # 1. Chuẩn bị dữ liệu UI
        target = co2_target.value
        ui_year = int(year_sel.value)
        country = country_sel.value
        
        # Lấy danh sách feature được chọn (checkbox = True) để gửi đi tối ưu
        selected_controls = [fc for fc in feature_controls if fc["checkbox"].value]
        
        if not selected_controls:
            recommend_text.object = "⚠️ Please select at least **one feature** to adjust."
            return
        
        # Đổi trạng thái nút bấm
        original_btn_name = btn_recommend.name
        btn_recommend.name = "Running Optimization..."
        btn_recommend.disabled = True
        recommend_text.object = "⏳ Calculating recommendations..."

        try:
            # 2. Lấy Base Values (Dữ liệu thực tế năm 2022 - Year-1)
            base_values = {}
            
            # A. CO2 (Lấy từ DF)
            prev_year = ui_year - 1
            df_country = df_all[df_all["Country"] == country]
            row_prev = df_country[df_country["Year"] == prev_year]
            
            if not row_prev.empty and "Co2_MtCO2" in row_prev.columns:
                val = row_prev.iloc[0]["Co2_MtCO2"]
                base_values["Co2_MtCO2"] = float(val) if pd.notnull(val) else 0.0
            else:
                base_values["Co2_MtCO2"] = 0.0

            # B. [QUAN TRỌNG] Lấy Feature từ UI
            for fc in feature_controls:
                feat_name = fc["name"]
                is_optimizing = fc["checkbox"].value
                
                if not is_optimizing:
                    # TRƯỜNG HỢP 1: KHÔNG TICK (User có thể đã sửa số ở Data 2023)
                    # Lấy giá trị từ ô nhập liệu Data 2023
                    val_float = float(fc["data_curr"].value)
                else:
                    # TRƯỜNG HỢP 2: CÓ TICK (Đang chạy tối ưu)
                    # Lấy giá trị gốc Data 2022 (từ DF hoặc parse từ UI data_prev)
                    # Ở đây ưu tiên lấy từ DataFrame cho chính xác
                    val_float = 0.0
                    if not row_prev.empty and feat_name in row_prev.columns:
                        raw = row_prev.iloc[0][feat_name]
                        val_float = float(raw) if pd.notnull(raw) else 0.0
                    else:
                        # Fallback parse từ UI Data 2022
                        try:
                            t = fc["data_prev"].object.replace(".","").replace(",",".")
                            val_float = float(t)
                        except: val_float = 0.0
                
                base_values[feat_name] = val_float
            # 3. Payload gửi API
            selected_features_payload = []
            for fc in selected_controls:
                selected_features_payload.append({
                    "feature": fc["name"],
                    "min_pct": float(fc["max_reduce"].value),
                    "max_pct": float(fc["max_increase"].value)
                })

            payload = {
                "country_name": country,
                "year": ui_year,
                "co2_target": float(target),
                "fixed_features": base_values,
                "feature_selection": selected_features_payload
            }

            # 4. Gọi API
            response = requests.post(API_URL, json=payload, timeout=160)
            
            if response.status_code == 200:
                res_data = response.json()
                pred_co2 = res_data["predicted_co2"]
                best_changes = res_data["best_change_pct"] 
                
                for feat_name, widget in predict_inputs.items():
                    base_val = base_values.get(feat_name, 0.0)
                    pct = best_changes.get(feat_name, 0.0)
                    rec_val = base_val * (1 + pct / 100.0)
                    widget.value = round(rec_val, 2)
                
                lines = [
                    f"Based on the information you provided, we recommend the following set of feature values "
                    f"to achieve CO₂ emissions as close as possible to your specified CO₂ target "
                    f"(<span style='color:#147a3c; font-weight:bold'>{target:.0f} MtCO₂</span>):"
                ]
                
                for fc in feature_controls:
                    fname = fc["name"]
                    pname = _pretty_name(fname)
                    
                    # Lấy giá trị base (Lúc này base chính là cái user nhập hoặc data gốc)
                    base_val = base_values.get(fname, 0.0)
                    pct = best_changes.get(fname, 0.0)
                    new_val = base_val * (1 + pct / 100.0)
                    
                    val_str = _fmt_value(new_val)
                    
                    change_str = ""
                    # Chỉ hiện % thay đổi nếu nó thực sự thay đổi (> 0.01%)
                    if abs(pct) > 0.01:
                        if pct < 0:
                            change_str = f" <span style='color:#ef4444'>({pct:.1f}%)</span>"
                        else:
                            change_str = f" <span style='color:#22c55e'>(+{pct:.1f}%)</span>"
                    
                    lines.append(f"- **{pname}**: {val_str}{change_str}")
                
                lines.append(f"\nUsing the recommended feature set above, the estimated CO₂ emissions are: <span style='color:#147a3c; font-weight:bold; font-size:1.1em'>{pred_co2:.2f} MtCO₂</span>")
                lines.append(
                    f"\n<span style='color:#d97706; font-style:italic; font-size:0.9em'>"
                    f"Note: There may be a discrepancy between the estimated CO₂ emissions and your specific target, "
                    f"as the optimization algorithm operates under mathematical constraints.</span>"
                )

                recommend_text.object = "\n".join(lines)
            else:
                recommend_text.object = f"**API Error:** {response.status_code} - {response.text}"

        except Exception as e:
            recommend_text.object = f"**System Error:** {str(e)}"
        
        finally:
            btn_recommend.name = original_btn_name
            btn_recommend.disabled = False
                
    btn_recommend.on_click(run_recommend)

    recommend_block = pn.Column(
        pn.Row(pn.Spacer(), btn_recommend, pn.Spacer(), sizing_mode="stretch_width"),
        pn.Spacer(height=15),
        recommend_text,
        css_classes=["rec-recommend-block"],
    )
    API_PREDICT_URL = "http://localhost:8002/predict_xgboost_v2"
    
    btn_predict = pn.widgets.Button(
        name="Predict", 
        button_type="success", 
        width=220, 
        css_classes=["run-btn", "rec-predict-btn"]
    )
    
    predict_result = pn.pane.Markdown(
        "", 
        align="center", 
        css_classes=["rec-predict-result"]
    )

    def run_predict(event):
        # 1. Lấy dữ liệu từ giao diện
        country = country_sel.value
        
        # Tạo dictionary features từ các ô input bên phải
        # predict_inputs đã được định nghĩa ở trên (dòng 230+)
        features_payload = {
            feat_name: widget.value 
            for feat_name, widget in predict_inputs.items()
        }

        # 2. Đổi trạng thái nút bấm (Feedback cho người dùng)
        btn_predict.name = "Predicting..."
        btn_predict.disabled = True
        predict_result.object = "Connecting to AI Model..."

        try:
            # 3. Gửi Request xuống API XGBoost (Port 8002)
            payload = {
                "country": country,
                "features": features_payload
            }
            
            # Timeout ngắn (5s) vì XGBoost chạy rất nhanh
            response = requests.post(API_PREDICT_URL, json=payload, timeout=5)

            if response.status_code == 200:
                data = response.json()
                pred_val = data.get("prediction", 0.0)
                
                # 4. Hiển thị kết quả đẹp
                predict_result.object = (
                    "The predicted total CO₂ emissions is:<br><br>"
                    f"<span style='color:#147a3c; font-size:22px; font-weight:700'>"
                    f"{pred_val:,.2f} MtCO₂"
                    f"</span>"
                )
            else:
                predict_result.object = f"API Error: {response.status_code}\n{response.text}"

        except Exception as e:
            predict_result.object = f"Connection Error (Check Port 8002):\n{str(e)}"
        
        finally:
            # 5. Reset trạng thái nút bấm
            btn_predict.name = "Predict"
            btn_predict.disabled = False

    btn_predict.on_click(run_predict)

    # Layout thẻ bên phải
    predict_card = pn.Card(
        pn.Column(
            *predict_inputs.values(), 
            pn.Spacer(height=15), 
            pn.Row(pn.Spacer(), btn_predict, pn.Spacer()), 
            pn.Spacer(height=10), 
            predict_result
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
        width=900
    )
    
    layout = pn.Row(
        left_panel, 
        pn.Spacer(width=20), 
        predict_card, 
        sizing_mode="stretch_width", 
        css_classes=["rec-main-row"]
    )

    return layout