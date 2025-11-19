import panel as pn
import requests
import pandas as pd
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, FactorRange
from bokeh.io import export_png

pn.extension(sizing_mode="stretch_width")

BACKEND = "http://localhost:8000"
PRED_URL = f"{BACKEND}/predict"
SENS_URL = f"{BACKEND}/sensitivity"
FEATURES_URL = f"{BACKEND}/features"

# ---- Widgets ----
country = pn.widgets.Select(name="Country", options=['Vietnam', 'USA', 'Germany'], value='Vietnam')
iso = pn.widgets.TextInput(name="ISO_Code", value="VNM")
year = pn.widgets.IntInput(name="Year", value=2025, step=1)

gdp = pn.widgets.FloatInput(name="GDP", value=342000.0, step=1000.0)
population = pn.widgets.FloatInput(name="Population", value=97_000_000.0, step=1000.0)
industry = pn.widgets.FloatInput(name="Industry_on_GDP", value=36.0, step=0.1)
hdi = pn.widgets.FloatInput(name="HDI", value=0.703, step=0.001)
education = pn.widgets.FloatInput(name="Gov Edu Spend %", value=4.1, step=0.1)
risk = pn.widgets.FloatInput(name="Climate Risk", value=25.0, step=0.1)
area = pn.widgets.FloatInput(name="Area_ha", value=33_121_200.0, step=1000.0)
forest = pn.widgets.FloatInput(name="Forest_Area_ha", value=14_250_000.0, step=1000.0)
deforest = pn.widgets.FloatInput(name="Deforest_Area_ha", value=20_000.0, step=10.0)
energy = pn.widgets.FloatInput(name="Energy_MWh", value=240_000_000.0, step=1000.0)
renewable = pn.widgets.FloatInput(name="Renewable Energy MWh", value=64_000_000.0, step=1000.0)

predict_btn = pn.widgets.Button(name="Dự báo CO₂", button_type="primary")
export_csv_btn = pn.widgets.Button(name="Export CSV", button_type="success")
export_png_btn = pn.widgets.Button(name="Export PNG", button_type="success")

# ---- KPI Pane (use HTML instead of Markdown) ----
co2_kpi = pn.pane.HTML(
    "<h3 style='font-size:22px; font-weight:600; margin:0;'>CO₂ dự báo: -</h3>"
)

# ---- Sensitivity ----
sens_source = ColumnDataSource(data=dict(feature=[], weight=[]))
# sens_plot = figure(x_range=[], height=320, title="Các yếu tố ảnh hưởng (Relative Importance)",
#                    toolbar_location=None, tools=None)
sens_plot = figure(x_range=FactorRange(), height=320, title="Các yếu tố ảnh hưởng (Relative Importance)",
                   toolbar_location=None, tools="")
sens_plot.vbar(x='feature', top='weight', width=0.8, source=sens_source)
sens_plot.xaxis.major_label_orientation = 1.2

# ---- Trend Plot ----
trend_source = ColumnDataSource(data=dict(x=[], y_base=[], y_high=[], y_low=[]))
trend_plot = figure(title="Forecast trend (Scenarios)", x_axis_label="Year", y_axis_label="CO₂ (MtCO₂)",
                    height=350, width=700)

trend_plot.line('x', 'y_base', source=trend_source, legend_label="Base", line_width=3, color="#1f77b4")
trend_plot.line('x', 'y_high', source=trend_source, legend_label="High Growth", line_width=3, color="#2ca02c")
trend_plot.line('x', 'y_low', source=trend_source, legend_label="Low Growth", line_width=3, color="#d62728")
trend_plot.legend.location = "top_left"


# ---- Backend Calls ----
def call_predict(payload):
    r = requests.post(PRED_URL, json=payload)
    r.raise_for_status()
    return r.json()["CO2_pred"]

def load_sensitivity():
    try:
        r = requests.post(SENS_URL, json={})
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return {}


# ---- Predict Handler ----
def on_predict(event=None):
    payload = {
        "Country": country.value,
        "ISO_Code": iso.value,
        "Year": year.value,
        "GDP": float(gdp.value),
        "Population": float(population.value),
        "Industry_on_GDP": float(industry.value),
        "HDI": float(hdi.value),
        "Government_Expenditure_on_Education": float(education.value),
        "Global_Climate_Risk_Index": float(risk.value),
        "Area_ha": float(area.value),
        "Forest_Area_ha": float(forest.value),
        "Deforest_Area_ha": float(deforest.value),
        "Energy_MWh": float(energy.value),
        "Renewable_Energy_MWh": float(renewable.value)
    }

    try:
        pred = call_predict(payload)
        co2_kpi.object = f"<h3 style='font-size:22px; font-weight:600; margin:0;'>CO₂ dự báo: {pred:.2f} MtCO₂</h3>"
    except Exception as e:
        co2_kpi.object = "<h3>CO₂ dự báo: Error</h3>"
        pn.state.notifications.error(f"Predict error: {e}")
        return

    sens = load_sensitivity()
    if sens:
        features = list(sens.keys())
        weights = [sens[f] for f in features]
        sens_source.data = {"feature": features, "weight": weights}
        sens_plot.x_range.factors = features

    start = year.value
    years_list = [start + i for i in range(8)]

    y_base, y_high, y_low = [], [], []

    for i, yr in enumerate(years_list):
        p_base = payload.copy()
        p_base["Year"] = yr
        p_high = payload.copy()
        p_high["Year"] = yr
        p_low = payload.copy()
        p_low["Year"] = yr

        p_high["GDP"] *= (1 + 0.03 * i)
        p_high["Population"] *= (1 + 0.01 * i)

        p_low["GDP"] *= (1 + 0.01 * i)
        p_low["Population"] *= (1 + 0.005 * i)

        y_base.append(call_predict(p_base))
        y_high.append(call_predict(p_high))
        y_low.append(call_predict(p_low))

    trend_source.data = {
        "x": years_list,
        "y_base": y_base,
        "y_high": y_high,
        "y_low": y_low,
    }

predict_btn.on_click(on_predict)

# ---- Export CSV ----
def on_export_csv(event):
    df = pd.DataFrame(trend_source.data)
    if df.empty:
        pn.state.notifications.warning("Không có dữ liệu để export.")
        return
    df.to_csv("co2_forecast_export.csv", index=False)
    pn.state.notifications.info("Đã export CSV.")

export_csv_btn.on_click(on_export_csv)


# ---- Export PNG ----
def on_export_png(event):
    try:
        export_png(trend_plot, filename="co2_forecast_plot.png")
        pn.state.notifications.info("Đã export PNG.")
    except Exception as e:
        pn.state.notifications.error(f"Lỗi export PNG: {e}")

export_png_btn.on_click(on_export_png)


# ---- UI Layout ----
sidebar = pn.Column(
    pn.pane.HTML("<h3 style='margin:10px 0;'>Menu</h3>"),
    pn.pane.HTML("<ul style='margin:0; padding-left:18px;'><li>Dashboard</li><li>Analysis</li><li>About</li></ul>"), 
    width=220, styles={'background': '#F7F9FB'}
)

header = pn.Row(
    pn.pane.HTML("<h1 style='font-size:28px; font-weight:700;'>CO₂ Analytics Dashboard</h1>"),
    pn.layout.Spacer(),
    co2_kpi,
)

inputs = pn.Card(
    "Nhập tham số",
    pn.Column(
        country, iso, year,
        pn.Row(gdp, population),
        pn.Row(industry, hdi),
        pn.Row(education, risk),
        pn.Row(area, forest),
        pn.Row(deforest, energy),
        pn.Row(renewable),
        pn.Row(predict_btn, export_csv_btn, export_png_btn),
    ),
    width=360, collapsible=True
)

analysis = pn.Column(
    pn.pane.Markdown("### Phân tích ảnh hưởng"),
    sens_plot,
    pn.pane.Markdown("### Forecast trend"),
    trend_plot,
)

main = pn.Column(
    header,
    pn.Row(inputs, analysis),
)

layout = pn.Row(sidebar, main)
layout.servable()
