"""
APP PRINCIPAL

Este aplicativo integra múltiplos motores financeiros:

1. Fluxo de obra (pré-chaves)
2. Simulação de investimentos
3. Simulação de financiamento (SAC/PRICE)
4. Simulação de reforma
5. Motor de decisão
6. Score de risco

Objetivo:
Transformar a compra do imóvel em uma decisão quantitativa estruturada.
"""

import streamlit as st
import pandas as pd

from config.profiles import PROFILES
from cashflow.construction import simulate_construction_phase
from finance.amortization import generate_amortization_schedule
from investments.portfolio import simulate_portfolio
from investments.monte_carlo import simulate_monte_carlo
from renovation.renovation_engine import estimate_renovation_cost
from risk.risk_engine import full_risk_assessment
from optimizer.decision_engine import generate_decision_strategies

from ui.styles import apply_global_styles
from ui.components import money, pct, status_badge, section
from ui.charts import (
    cashflow_stacked_chart,
    portfolio_composition_chart,
    monte_carlo_histogram,
    renovation_pie_chart,
    amortization_chart,
    strategy_score_chart,
    risk_heatmap,
)


st.set_page_config(
    page_title="Planejamento Financeiro Imobiliário",
    page_icon="🏢",
    layout="wide",
)

apply_global_styles()


st.title("🏢 Planejamento Financeiro Imobiliário")
st.caption(
    "Motor de decisão financeira completo para compra de imóvel na planta."
)


with st.sidebar:
    st.header("Configurações")

    selected_profile_name = st.selectbox(
        "Perfil",
        list(PROFILES.keys()),
        help="Selecione um perfil de comprador predefinido.",
    )

    profile = PROFILES[selected_profile_name]

    st.divider()

    monthly_budget = st.number_input(
        "Orçamento total mensal durante a construção",
        min_value=0.0,
        value=float(6_000 if profile.name == "Vinicius & Ju" else 1_500),
        step=100.0,
        help="Total acumulado disponível a cada mês para custos de construção e economias.",
    )

    minimum_saving_floor = st.number_input(
        "Piso mínimo de economias mensais",
        min_value=0.0,
        value=float(1_000 if profile.name == "Vinicius & Ju" else 300),
        step=100.0,
        help="Economias mínimas obrigatórias a cada mês mesmo se os gastos ultrapassarem o orçamento.",
    )

    construction_curve = st.selectbox(
        "Curva de evolução de obra",
        ["Linear", "Curva em S", "Acumulado no final"],
        index=1,
        help="Controla como a evolução da construção cresce até a entrega das chaves.",
    )

    annual_installment = st.number_input(
        "Parcela anual opcional",
        min_value=0.0,
        value=0.0,
        step=500.0,
    )

    st.divider()

    renovation_package = st.selectbox(
        "Pacote de reforma",
        ["Básico", "Recomendado", "Premium"],
        index=1,
    )

    num_ares = st.number_input(
        "Número de aparelhos de ar-condicionado",
        min_value=0,
        max_value=5,
        value=3
        )

    annual_inflation = st.number_input(
        "Inflação anual da reforma",
        min_value=0.0,
        value=0.045,
        step=0.005,
        format="%.3f",
    )

    monthly_living_expenses = st.number_input(
        "Despesas de vida mensais estimadas após as chaves",
        min_value=0.0,
        value=float(profile.household_income * 0.55),
        step=100.0,
        help="Usado para calcular os requisitos de reserva de emergência.",
    )

    monte_carlo_runs = st.slider(
        "Simulações de Monte Carlo",
        min_value=1000,
        max_value=20000,
        value=5000,
        step=1000,
    )


construction_df = simulate_construction_phase(
    months=profile.months_until_keys,
    builder_installment=profile.monthly_builder_installment,
    initial_construction_evolution=profile.initial_construction_evolution,
    curve_type=construction_curve,
    monthly_budget=monthly_budget,
    minimum_saving_floor=minimum_saving_floor,
    annual_installment=annual_installment,
)

portfolio_df = simulate_portfolio(
    contributions=construction_df["Monthly Savings"],
    months_until_keys=profile.months_until_keys,
)

mc = simulate_monte_carlo(
    monthly_contributions=construction_df["Monthly Savings"],
    months_until_keys=profile.months_until_keys,
    simulations=monte_carlo_runs,
)

renovation_df = estimate_renovation_cost(
    apartment_size_m2=profile.apartment_size_m2 or 50,
    package=renovation_package,
    months_until_keys=profile.months_until_keys,
    annual_inflation=annual_inflation,
    num_ares=num_ares,
)

amortization_df = generate_amortization_schedule(
    system=profile.financing_system,
    principal=profile.financing_ceiling,
    annual_rate=profile.annual_interest_rate,
    term_months=profile.term_months,
)


# Ajuste para refletir valores aprovados pela Caixa
amortization_df.loc[0, "Payment"] = profile.approved_first_installment

if profile.approved_last_installment:
    amortization_df.loc[len(amortization_df)-1, "Payment"] = profile.approved_last_installment


projected_cash_at_keys = float(portfolio_df["Total Portfolio"].iloc[-1])
total_contributed = float(portfolio_df["Total Contributed"].iloc[-1])
investment_gain = float(portfolio_df["Investment Gain"].iloc[-1])
renovation_cost = float(renovation_df["Inflated Cost"].sum())
renovation_coverage = projected_cash_at_keys / renovation_cost if renovation_cost else 0

avg_stress_ratio = float(construction_df["Stress Ratio"].mean())
max_stress_ratio = float(construction_df["Stress Ratio"].max())
peak_stress_month = int(construction_df.sort_values("Stress Ratio", ascending=False).iloc[0]["Month"])

risk = full_risk_assessment(
    first_installment=profile.approved_first_installment,
    household_income=profile.household_income,
    avg_stress_ratio=avg_stress_ratio,
    max_stress_ratio=max_stress_ratio,
    projected_cash=projected_cash_at_keys,
    renovation_cost=renovation_cost,
)

strategies_df = generate_decision_strategies(
    cash_at_keys=projected_cash_at_keys,
    renovation_cost=renovation_cost,
    monthly_expenses=monthly_living_expenses,
    outstanding_balance=profile.financing_ceiling,
    financing_annual_rate=profile.annual_interest_rate,
)

best_strategy = strategies_df.iloc[0]
strategy_display_labels = {
    "Aggressive Amortization": "Amortização agressiva",
    "Balanced": "Equilibrada",
    "Safety First": "Prioridade de segurança",
    "Quality of Life": "Qualidade de vida",
}
best_strategy_label = strategy_display_labels.get(
    best_strategy["Strategy"],
    best_strategy["Strategy"],
)


tab_exec, tab_cashflow, tab_investments, tab_financing, tab_renovation, tab_decision, tab_risk, tab_data = st.tabs(
    [
        "Geral",
        "🏗️ Fluxo de Obra",
        "💰 Investimentos",
        "🏦 Financiamento",
        "🛠️ Reforma",
        "🧠 Estratégia",
        "⚠️ Risco",
        "📁 Dados",
    ]
)


with tab_exec:
    section(
        "Visão Executiva",
        "Visão geral da posição financeira na entrega das chaves e da prontidão para decidir.",
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Valor projetado em caixa às chaves",
        money(projected_cash_at_keys),
        help="Valor projetado do portfólio de investimentos às chaves.",
    )

    c2.metric(
        "Ganhos de investimento",
        money(investment_gain),
        help="Valor do portfólio menos contribuições totais.",
    )

    c3.metric(
        "Cobertura de reforma",
        pct(renovation_coverage),
        help="Caixa às chaves dividido pelo custo projetado de reforma.",
    )

    c4.metric(
        "Score de risco",
        f'{risk["overall"]["score"]}/100',
        status_badge(risk["overall"]["status"]),
    )

    st.divider()

    if renovation_coverage < 1:
        st.error("🚨 A reforma não está totalmente coberta. Evite amortizar o financiamento.")
    elif risk["overall"]["status"] == "red":
        st.warning("⚠️ Alto risco financeiro. Preserve liquidez.")
    else:
        st.success("✅ Situação equilibrada. Amortização controlada é viável.")


    c5, c6, c7 = st.columns(3)

    c5.metric("Mês de pico de estresse", f"Mês {peak_stress_month}")
    c6.metric("Melhor estratégia", best_strategy_label)
    c7.metric("P50 do Monte Carlo", money(mc["p50"]))

    st.info(
        f"""
        Estratégia recomendada: **{best_strategy_label}**.

        Essa estratégia aloca aproximadamente:
        - {money(best_strategy["Emergency Reserve"])} para reserva de emergência
        - {money(best_strategy["Renovation"])} para reforma
        - {money(best_strategy["Loan Amortization"])} para amortização de empréstimo
        """
    )

    st.plotly_chart(
        portfolio_composition_chart(portfolio_df),
        use_container_width=True,
        key="portfolio_cockpit",
    )

    st.plotly_chart(
        risk_heatmap(risk),
        use_container_width=True,
        key="risk_heatmap_cockpit",
    )


with tab_cashflow:
    section(
        "Fase de construção — fluxo de caixa",
        "Acompanha a evolução mensal da obra, a poupança obrigatória, a pressão de gastos e o saldo acumulado.",
    )

    st.plotly_chart(
    cashflow_stacked_chart(construction_df, renda=profile.household_income),
    use_container_width=True,
    key="cashflow_chart"
    )

    construction_display = construction_df.rename(columns={
        "Month": "Mês",
        "Builder Installment": "Prestação do construtor",
        "Construction Evolution": "Evolução da obra",
        "Annual Installment": "Parcela anual",
        "Total Cost": "Custo total",
        "Monthly Savings": "Poupança mensal",
        "Accumulated Savings": "Poupança acumulada",
        "Real Monthly Spending": "Gasto real mensal",
        "Stress Amount": "Valor de estresse",
        "Stress Ratio": "Razão de estresse",
    })

    st.dataframe(
        construction_display.style.format({
            "Prestação do construtor": "R$ {:,.2f}",
            "Evolução da obra": "R$ {:,.2f}",
            "Parcela anual": "R$ {:,.2f}",
            "Custo total": "R$ {:,.2f}",
            "Poupança mensal": "R$ {:,.2f}",
            "Poupança acumulada": "R$ {:,.2f}",
            "Gasto real mensal": "R$ {:,.2f}",
            "Valor de estresse": "R$ {:,.2f}",
            "Razão de estresse": "{:.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )


with tab_investments:
    section(
        "Investimentos",
        "Alocação dinâmica da estratégia de risco, passando de equilibrada para ultra-conservadora conforme a entrega se aproxima.",
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Total contribuído", money(total_contributed))
    c2.metric("Portfólio esperado", money(projected_cash_at_keys))
    c3.metric("Ganho esperado", money(investment_gain))

    st.plotly_chart(
            portfolio_composition_chart(portfolio_df),
            use_container_width=True,
            key="portfolio_investments"
    )



    st.subheader("Simulação Monte Carlo")
    c4, c5, c6 = st.columns(3)
    c4.metric("P5", money(mc["p5"]))
    c5.metric("P50", money(mc["p50"]))
    c6.metric("P95", money(mc["p95"]))

    st.plotly_chart(
        monte_carlo_histogram(
            mc["values"],
            mc["p5"],
            mc["p50"],
            mc["p95"],
        ),
        use_container_width=True,
        key="monte_carlo_chart"
    )


with tab_financing:
    section(
        "Financiamento",
        f"Tabela completa de amortização com o sistema {profile.financing_system}.",
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Principal", money(profile.financing_ceiling))
    c2.metric("Taxa anual", pct(profile.annual_interest_rate))
    c3.metric("Prazo", f"{profile.term_months} meses")
    c4.metric("Primeira parcela", money(amortization_df["Payment"].iloc[0]))

    st.plotly_chart(
        amortization_chart(amortization_df),
        use_container_width=True,
        key="amortization_chart"
    )

    amortization_display = amortization_df.rename(columns={
        "Month": "Mês",
        "Opening Balance": "Saldo inicial",
        "Interest": "Juros",
        "Amortization": "Amortização",
        "Payment": "Parcela",
        "Ending Balance": "Saldo final",
    })

    st.dataframe(
        amortization_display.style.format({
            "Saldo inicial": "R$ {:,.2f}",
            "Juros": "R$ {:,.2f}",
            "Amortização": "R$ {:,.2f}",
            "Parcela": "R$ {:,.2f}",
            "Saldo final": "R$ {:,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )


with tab_renovation:
    section(
        "Reforma e móveis",
        "Estimativa ajustada pela inflação por categoria de custo e pacote selecionado.",
    )

    c1, c2 = st.columns(2)
    c1.metric("Custo projetado da reforma", money(renovation_cost))
    c2.metric("Pacote", renovation_package)

    st.plotly_chart(
        renovation_pie_chart(renovation_df),
        use_container_width=True,
        key="renovation_chart"
        )

    renovation_display = renovation_df.rename(columns={
        "Category": "Categoria",
        "Base Cost": "Custo base",
        "Inflated Cost": "Custo inflado",
        "Cost per m²": "Custo por m²",
        "Share": "Participação",
    })
    renovation_display["Categoria"] = renovation_display["Categoria"].replace({
        "Civil Work": "Obra civil",
        "Cabinetry": "Móveis planejados",
        "Appliances": "Eletrodomésticos",
        "Lighting": "Iluminação",
        "Ac": "Ar-condicionado",
        "Decor": "Decoração",
    })

    st.dataframe(
        renovation_display.style.format({
            "Custo base": "R$ {:,.2f}",
            "Custo inflado": "R$ {:,.2f}",
            "Custo por m²": "R$ {:,.2f}",
            "Participação": "{:.1%}",
        }),
        use_container_width=True,
        hide_index=True,
    )


with tab_decision:
    section(
        "Estratégia na entrega das chaves",
        "Classifica as opções de uso do caixa entre reforma, reserva de emergência e amortização do empréstimo.",
    )

    st.plotly_chart(
        strategy_score_chart(strategies_df),
        use_container_width=True,
        key="strategy_chart"
        )

    strategies_display = strategies_df.rename(columns={
        "Strategy": "Estratégia",
        "Emergency Reserve": "Reserva de emergência",
        "Renovation": "Reforma",
        "Loan Amortization": "Amortização do empréstimo",
        "Idle Cash": "Caixa ocioso",
        "Renovation Coverage": "Cobertura da reforma",
        "Reserve Months": "Meses de reserva",
        "Financial Score": "Score financeiro",
        "Safety Score": "Score de segurança",
        "Quality of Life Score": "Score de qualidade de vida",
        "Total Score": "Score total",
    })
    strategies_display["Estratégia"] = strategies_display["Estratégia"].replace({
        "Aggressive Amortization": "Amortização agressiva",
        "Balanced": "Equilibrada",
        "Safety First": "Prioridade de segurança",
        "Quality of Life": "Qualidade de vida",
    })

    st.dataframe(
        strategies_display.style.format({
            "Reserva de emergência": "R$ {:,.2f}",
            "Reforma": "R$ {:,.2f}",
            "Amortização do empréstimo": "R$ {:,.2f}",
            "Caixa ocioso": "R$ {:,.2f}",
            "Cobertura da reforma": "{:.1%}",
            "Meses de reserva": "{:.1f}",
            "Score financeiro": "{:.1f}",
            "Score de segurança": "{:.1f}",
            "Score de qualidade de vida": "{:.1f}",
            "Score total": "{:.1f}",
        }),
        use_container_width=True,
        hide_index=True,
    )


with tab_risk:
    section(
        "Avaliação de risco",
        "Combina comprometimento da renda, estresse da poupança e cobertura da reforma em uma nota de 0 a 100.",
    )

    st.plotly_chart(
        risk_heatmap(risk),
        use_container_width=True,
        key="risk_heatmap_tab"
        )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Compromisso com a renda",
        pct(risk["income_commitment"]["ratio"]),
        status_badge(risk["income_commitment"]["status"]),
    )

    c2.metric(
        "Estresse da poupança",
        f'{risk["savings_stress"]["score"]:.1f}/100',
        status_badge(risk["savings_stress"]["status"]),
    )

    renovation_coverage_ratio = float(
        risk["renovation_coverage"]["coverage"]
        if risk["renovation_coverage"]["coverage"] is not None
        else 0
    )

    c3.metric(
        "Cobertura da reforma",
        pct(renovation_coverage_ratio),
        delta=(
            f"{(renovation_coverage_ratio - 1) * 100:.1f}% "
            f"({status_badge(risk['renovation_coverage']['status'])})"
        ),
    )

    c4.metric(
        "Risco geral",
        f'{risk["overall"]["score"]:.1f}/100',
        status_badge(risk["overall"]["status"]),
    )


with tab_data:
    section(
        "Dados do modelo",
        "Saídas brutas para validação, auditoria e exportação.",
    )

    st.subheader("Perfil selecionado")
    st.json(profile.__dict__)

    st.subheader("Fluxo de caixa da construção")
    st.dataframe(construction_df, use_container_width=True, hide_index=True)

    st.subheader("Portfólio")
    st.dataframe(portfolio_df, use_container_width=True, hide_index=True)

    st.subheader("Reforma")
    st.dataframe(renovation_df, use_container_width=True, hide_index=True)

    st.subheader("Estratégias de decisão")
    st.dataframe(strategies_df, use_container_width=True, hide_index=True)