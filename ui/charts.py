import plotly.express as px
import plotly.graph_objects as go


def cashflow_stacked_chart(df):
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["Month"],
        y=df["Builder Installment"],
        name="Builder Installment",
    ))

    fig.add_trace(go.Bar(
        x=df["Month"],
        y=df["Construction Evolution"],
        name="Construction Evolution",
    ))

    fig.add_trace(go.Bar(
        x=df["Month"],
        y=df["Annual Installment"],
        name="Annual Installment",
    ))

    fig.add_trace(go.Scatter(
        x=df["Month"],
        y=df["Monthly Savings"],
        mode="lines+markers",
        name="Monthly Savings",
    ))

    fig.update_layout(
        barmode="stack",
        title="Construction Phase Cash Flow",
        xaxis_title="Month",
        yaxis_title="BRL",
        template="plotly_white",
        height=460,
    )

    return fig


def portfolio_composition_chart(df):
    asset_cols = ["Liquidity", "PostFixed", "TaxFree", "ControlledRisk"]

    fig = go.Figure()

    for col in asset_cols:
        fig.add_trace(go.Scatter(
            x=df["Month"],
            y=df[col],
            stackgroup="one",
            name=col,
        ))

    fig.update_layout(
        title="Portfolio Composition Over Time",
        xaxis_title="Month",
        yaxis_title="BRL",
        template="plotly_white",
        height=460,
    )

    return fig


def monte_carlo_histogram(values, p5, p50, p95):
    fig = px.histogram(
        x=values,
        nbins=60,
        title="Monte Carlo Distribution - Cash at Keys",
        template="plotly_white",
    )

    for value, label in [(p5, "P5"), (p50, "P50"), (p95, "P95")]:
        fig.add_vline(
            x=value,
            line_dash="dash",
            annotation_text=label,
            annotation_position="top",
        )

    fig.update_layout(
        xaxis_title="Projected Portfolio Value",
        yaxis_title="Frequency",
        height=460,
    )

    return fig


def renovation_pie_chart(df):
    fig = px.pie(
        df,
        values="Inflated Cost",
        names="Category",
        title="Renovation Cost Breakdown",
        hole=0.42,
        template="plotly_white",
    )

    fig.update_layout(height=430)

    return fig


def amortization_chart(df):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["Month"],
        y=df["Payment"],
        name="Payment",
        mode="lines",
    ))

    fig.add_trace(go.Scatter(
        x=df["Month"],
        y=df["Interest"],
        name="Interest",
        mode="lines",
    ))

    fig.add_trace(go.Scatter(
        x=df["Month"],
        y=df["Amortization"],
        name="Amortization",
        mode="lines",
    ))

    fig.update_layout(
        title="Financing Schedule",
        xaxis_title="Month",
        yaxis_title="BRL",
        template="plotly_white",
        height=460,
    )

    return fig


def strategy_score_chart(df):
    fig = px.bar(
        df,
        x="Strategy",
        y="Total Score",
        color="Strategy",
        title="Decision Strategy Ranking",
        template="plotly_white",
    )

    fig.update_layout(height=420, showlegend=False)

    return fig


def risk_heatmap(risk_dict):
    labels = [
        "Income Commitment",
        "Savings Stress",
        "Renovation Coverage",
        "Overall",
    ]

    values = [
        risk_dict["income_commitment"]["score"],
        risk_dict["savings_stress"]["score"],
        risk_dict["renovation_coverage"]["score"],
        risk_dict["overall"]["score"],
    ]

    fig = go.Figure(data=go.Heatmap(
        z=[values],
        x=labels,
        y=["Risk Score"],
        colorscale=[
            [0, "#dc2626"],
            [0.5, "#facc15"],
            [1, "#16a34a"],
        ],
        zmin=0,
        zmax=100,
        text=[[round(v, 1) for v in values]],
        texttemplate="%{text}",
    ))

    fig.update_layout(
        title="Risk Score Heatmap",
        template="plotly_white",
        height=280,
    )

    return fig