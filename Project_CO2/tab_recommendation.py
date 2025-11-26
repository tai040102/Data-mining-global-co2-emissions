# tab_recommendation.py
import panel as pn

def create_recommendation_view():
    header = pn.pane.Markdown("## Recommendation Engine")

    country_sel = pn.widgets.Select(
        name="Country", options=["Vietnam", "Thailand"], value="Vietnam"
    )
    year_sel = pn.widgets.Select(
        name="Year", options=[2026, 2027, 2028], value=2026
    )

    feature_checkbox = pn.widgets.Checkbox(name="GDP", value=True)
    cost_slider = pn.widgets.FloatSlider(
        name="Cost Level", start=0, end=1, step=0.1, value=0.5
    )
    cost_slider.bar_color = "#33cc7a"

    btn_run = pn.widgets.Button(name="Recommend", button_type="default", width=220, css_classes=["run-btn"])
    result_box = pn.pane.Markdown("")

    def run_recommend(event):
        result_box.object = (
            "**Recommendation executed**\n\n"
            f"- Feature GDP: {feature_checkbox.value}\n"
            f"- Cost Level: {cost_slider.value}"
        )

    btn_run.on_click(run_recommend)

    return pn.Column(
        header,
        pn.Row(country_sel, year_sel),
        pn.Spacer(height=10),
        pn.pane.Markdown("### Adjust Feature Impact"),
        pn.Row(feature_checkbox, cost_slider),
        pn.Spacer(height=15),
        pn.Row(
            pn.Spacer(),
            btn_run,
            pn.Spacer(),
            sizing_mode="stretch_width"
        ),
        pn.Spacer(height=20),
        result_box,
    )
