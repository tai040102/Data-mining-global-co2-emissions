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
API_URL = "http://localhost:8000/recommend"

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
        value="Vietnam" if "Vietnam" in countries else countries[0],
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
        data_curr = pn.pane.HTML(
            '<input type="number" class="rec-num-input" value="0" disabled />',
            css_classes=["rec-data-curr"],
        )
        INPUT_STYLE_NO_BOX = "border:none; background:transparent; width:100%; text-align:right; color:#333;"
        def toggle_row(event, mr=max_reduce, mi=max_increase, dc=data_curr, dp=data_prev):
                is_checked = event.new
                
                mr.disabled = not is_checked
                mi.disabled = not is_checked
                
                # Lấy giá trị hiện tại của Data 2022
                try:
                    val_text = dp.object.replace(",", "") 
                    val_float = float(val_text)
                except:
                    val_float = 0

                if is_checked:
                    # Nếu tick -> Ẩn hoàn toàn (display:none)
                    # Lưu ý: value vẫn format .2f để chuẩn dữ liệu
                    dc.object = f'<input type="number" class="rec-num-input" value="{val_float:.2f}" style="display:none;" />'
                else:
                    # Nếu bỏ tick -> Hiện lại nhưng KHÔNG CÓ KHUNG (dùng style NO_BOX)
                    # Format value="{val_float:.2f}" để lấy 2 số thập phân
                    dc.object = (
                        f'<input type="number" class="rec-num-input" '
                        f'value="{val_float:.2f}" '
                        f'disabled '
                        f'style="{INPUT_STYLE_NO_BOX}" />'
                    )

        cb.param.watch(toggle_row, 'value')

        feature_controls.append(
            dict(
                name=feat, checkbox=cb, data_prev=data_prev,
                max_reduce=max_reduce, max_increase=max_increase, data_curr=data_curr,
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

        header_prev.object = f"**Data {ui_year - 1}**"
        header_curr.object = f"**Data {ui_year}**"

        prev_year = ui_year - 1
        curr_year = ui_year

        df_country = df_all[df_all["Country"] == country_sel.value]
        row_prev = df_country[df_country["Year"] == prev_year]
        
        for fc in feature_controls:
            col = fc["name"]
            is_checked = fc["checkbox"].value

            # 1. Lấy Data 2022 (Prev)
            val_prev = 0
            if not row_prev.empty and col in row_prev.columns:
                val_prev = row_prev.iloc[0][col]
            
            val_prev = 0 if pd.isna(val_prev) else val_prev
            fc["data_prev"].object = _fmt_value(val_prev)

            # 2. Xử lý Data 2023 (Curr)
            raw_val = float(val_prev)

            if is_checked:
                # Nếu đang chỉnh sửa -> Ẩn
                fc["data_curr"].object = (
                    f'<input type="number" class="rec-num-input" value="{raw_val:.2f}" style="display:none;" />'
                )
            else:
                # Nếu hiển thị -> Bỏ khung viền + Format 2 số thập phân
                fc["data_curr"].object = (
                    f'<input type="number" class="rec-num-input" '
                    f'value="{raw_val:.2f}" '
                    f'disabled '
                    f'style="{INPUT_STYLE_NO_BOX}" />'
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
            prev_year = ui_year - 1
            df_country = df_all[df_all["Country"] == country]
            row_prev = df_country[df_country["Year"] == prev_year]
            
            base_values = {}
            if not row_prev.empty:
                cols_to_get = FEATURES + ["Co2_MtCO2"] 
                for col in cols_to_get:
                    if col in row_prev.columns:
                        val = row_prev.iloc[0][col]
                        base_values[col] = float(val) if pd.notnull(val) else 0.0
            
            # 3. Payload gửi API
            selected_features_payload = []
            for fc in selected_controls:
                selected_features_payload.append({
                    "feature": fc["name"],
                    "min_pct": float(fc["max_reduce"].value),
                    "max_pct": float(fc["max_increase"].value)
                })

            payload = {
                "country": country,
                "year": ui_year,
                "target": float(target),
                "base_values": base_values,
                "selected_features": selected_features_payload
            }

            # 4. Gọi API
            response = requests.post(API_URL, json=payload, timeout=60)
            
            if response.status_code == 200:
                res_data = response.json()
                pred_co2 = res_data["predicted_co2"]
                best_changes = res_data["best_change_pct"] 
                
                # ========== 5. FORMAT TEXT KẾT QUẢ (GIỐNG HÌNH MẪU) ==========
                
                # Header
                lines = [
                    f"Based on the information you provided, we recommend the following set of feature values "
                    f"to achieve CO₂ emissions as close as possible to your specified CO₂ target "
                    f"(<span style='color:#147a3c; font-weight:bold'>{target:.0f} MtCO₂</span>):"
                ]
                
                # List Features: Hiển thị TẤT CẢ các biến (được tick và không được tick)
                for fc in feature_controls:
                    fname = fc["name"]
                    pname = _pretty_name(fname)
                    
                    # Lấy giá trị gốc
                    base_val = base_values.get(fname, 0.0)
                    
                    # Lấy % thay đổi từ API (nếu không được chọn hoặc không thay đổi thì là 0)
                    pct = best_changes.get(fname, 0.0)
                    
                    # Tính giá trị mới: New = Base * (1 + pct/100)
                    new_val = base_val * (1 + pct / 100.0)
                    
                    # Format số liệu (dùng hàm _fmt_value có sẵn)
                    val_str = _fmt_value(new_val)
                    
                    # Format phần % thay đổi (Tô màu)
                    change_str = ""
                    if pct < -0.01:
                        # Giảm -> Màu Đỏ
                        change_str = f" <span style='color:#ef4444'>({pct:.1f}%)</span>"
                    elif pct > 0.01:
                        # Tăng -> Màu Xanh lá
                        change_str = f" <span style='color:#22c55e'>(+{pct:.1f}%)</span>"
                    # Nếu bằng 0 thì không hiện gì thêm
                    
                    lines.append(f"- **{pname}**: {val_str}{change_str}")
                
                # Prediction Footer
                lines.append(
                    f"\nUsing the recommended feature set above, the estimated CO₂ emissions are: "
                    f"<span style='color:#147a3c; font-weight:bold; font-size:1.1em'>{pred_co2:.0f} MtCO₂</span>"
                )
                
                # Note Footer (Màu vàng/cam)
                lines.append(
                    f"\n<span style='color:#d97706; font-style:italic; font-size:0.9em'>"
                    f"Note: There may be a discrepancy between the estimated CO₂ emissions and your specific target, "
                    f"as the optimization algorithm operates under mathematical constraints.</span>"
                )

                recommend_text.object = "\n".join(lines)

                # [Optional] Cập nhật UI input Data 2023 nếu cần
                # ...
                        
            else:
                recommend_text.object = f" **API Error:** {response.status_code} - {response.text}"

        except Exception as e:
            recommend_text.object = f" **System Error:** {str(e)}"
        
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