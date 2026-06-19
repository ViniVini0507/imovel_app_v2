import plotly.express as px
import plotly.graph_objects as go


def cashflow_stacked_chart(df):
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["Month"],
        y=df["Builder Installment"],
        name="Prestação do construtor",
    ))

    fig.add_trace(go.Bar(
        x=df["Month"],
        y=df["Construction Evolution"],
        name="Evolução da obra",
    ))

    fig.add_trace(go.Bar(
        x=df["Month"],
        y=df["Annual Installment"],
        name="Parcela anual",
    ))

    fig.add_trace(go.Scatter(
        x=df["Month"],
        y=df["Monthly Savings"],
        mode="lines+markers",
        name="Poupança mensal",
    ))

    fig.update_layout(
        barmode="stack",
        title="Fluxo de caixa da fase de construção",
        xaxis_title="Mês",
        yaxis_title="BRL",
        template="plotly_white",
        height=460,
    )

    return fig


def portfolio_composition_chart(df):
    asset_cols = ["Liquidity", "PostFixed", "TaxFree", "ControlledRisk"]
    labels = {
        "Liquidity": "Liquidez",
        "PostFixed": "Pós-fixado",
        "TaxFree": "Isento de IR",
        "ControlledRisk": "Risco controlado",
    }

    fig = go.Figure()

    for col in asset_cols:
        fig.add_trace(go.Scatter(
            x=df["Month"],
            y=df[col],
            stackgroup="one",
            name=labels.get(col, col),
        ))

    fig.update_layout(
        title="Composição do portfólio ao longo do tempo",
        xaxis_title="Mês",
        yaxis_title="BRL",
        template="plotly_white",
        height=460,
    )

    return fig


def monte_carlo_histogram(values, p5, p50, p95):
    import numpy as np

    mean_value = float(np.mean(values)) if len(values) else 0

    fig = px.histogram(
        x=values,
        nbins=60,
        title="Distribuição Monte Carlo - caixa nas chaves",
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
        xaxis_title="Valor projetado do portfólio",
        yaxis_title="Frequência",
        height=460,
    )

    fig.add_vline(
        x=mean_value,
        line_color="purple",
        annotation_text="Média",
    )

    return fig


def renovation_pie_chart(df):
    category_labels = {
        "civil_work": "Obra civil",
        "cabinetry": "Móveis planejados",
        "appliances": "Eletrodomésticos",
        "lighting": "Iluminação",
        "ac": "Ar-condicionado",
        "decor": "Decoração",
        "Civil Work": "Obra civil",
        "Cabinetry": "Móveis planejados",
        "Appliances": "Eletrodomésticos",
        "Lighting": "Iluminação",
        "Ac": "Ar-condicionado",
        "Decor": "Decoração",
    }

    chart_df = df.copy()
    chart_df["Category"] = chart_df["Category"].map(category_labels).fillna(chart_df["Category"])

    fig = px.pie(
        chart_df,
        values="Inflated Cost",
        names="Category",
        title="Distribuição do custo da reforma",
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
        name="Parcela",
        mode="lines",
    ))

    fig.add_trace(go.Scatter(
        x=df["Month"],
        y=df["Interest"],
        name="Juros",
        mode="lines",
    ))

    fig.add_trace(go.Scatter(
        x=df["Month"],
        y=df["Amortization"],
        name="Amortização",
        mode="lines",
    ))

    fig.update_layout(
        title="Cronograma de financiamento",
        xaxis_title="Mês",
        yaxis_title="BRL",
        template="plotly_white",
        height=460,
    )

    return fig


def strategy_score_chart(df):
    strategy_labels = {
        "Aggressive Amortization": "Amortização agressiva",
        "Balanced": "Equilibrada",
        "Safety First": "Prioridade de segurança",
        "Quality of Life": "Qualidade de vida",
    }

    chart_df = df.copy()
    chart_df["Strategy"] = chart_df["Strategy"].map(strategy_labels).fillna(chart_df["Strategy"])

    fig = px.bar(
        chart_df,
        x="Strategy",
        y="Total Score",
        color="Strategy",
        title="Ranking das estratégias",
        template="plotly_white",
    )

    fig.update_layout(height=420, showlegend=False)

    return fig


def risk_heatmap(risk_dict):
    labels = [
        "Compromisso com a renda",
        "Estresse da poupança",
        "Cobertura da reforma",
        "Geral",
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
        y=["Pontuação de risco"],
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
        title="Mapa de calor do risco",
        template="plotly_white",
        height=280,
    )

    return fig