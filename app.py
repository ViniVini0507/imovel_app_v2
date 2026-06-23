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
import os
import json

DATA_FILE = "real_data.json"


def load_real_data(default_df):
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    else:
        return {
            int(row["Month"]): {
                "savings": float(row["Monthly Savings"]),
                "evolution": float(row["Construction Evolution"]),
            }
            for _, row in default_df.iterrows()
        }


def save_real_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

from config.profiles import PROFILES
from cashflow.construction import simulate_construction_phase
from finance.amortization import generate_amortization_schedule, simulate_extra_amortization
from investments.portfolio import simulate_portfolio, get_current_allocation
from investments.monte_carlo import simulate_monte_carlo, explain_monte_carlo
from renovation.renovation_engine import estimate_renovation_cost
from optimizer.decision_engine import generate_decision_strategies

from ui.styles import apply_global_styles
from ui.components import money, pct, section
from ui.charts import (
    cashflow_stacked_chart,
    portfolio_composition_chart,
    monte_carlo_histogram,
    renovation_pie_chart,
    amortization_chart,
    strategy_score_chart,
)


def render_savings_indicator(projected_cash_at_keys: float, renovation_cost: float, months_remaining: int) -> float:
    """Mostra o indicador 'estou poupando o suficiente?' e retorna o gap em R$."""
    gap = projected_cash_at_keys - renovation_cost
    coverage_ratio = projected_cash_at_keys / renovation_cost if renovation_cost > 0 else 1.0

    if coverage_ratio >= 1.15:
        icon, message = "🟢", "Você está poupando mais do que precisa para cobrir a reforma."
    elif coverage_ratio >= 0.95:
        icon, message = "🟡", "Você está perto da meta, mas com pouca margem de segurança."
    else:
        icon, message = "🔴", "Você não está poupando o suficiente para cobrir a reforma."

    st.markdown(f"#### {icon} Estou poupando o suficiente?")

    c1, c2, c3 = st.columns(3)
    c1.metric("Caixa projetado nas chaves", money(projected_cash_at_keys))
    c2.metric("Custo projetado da reforma", money(renovation_cost))
    c3.metric("Gap (caixa − reforma)", money(gap), delta=f"{(coverage_ratio - 1) * 100:.1f}%")

    st.markdown(f"**{message}**")

    if gap < 0 and months_remaining > 0:
        extra_per_month_needed = abs(gap) / months_remaining
        st.error(
            f"Para fechar essa diferença, você precisaria poupar aproximadamente "
            f"**{money(extra_per_month_needed)} a mais por mês** nos próximos {months_remaining} meses."
        )

    return gap


def render_savings_simulator(months_until_keys: int, renovation_cost: float) -> None:
    """Simulador: 'e se eu poupasse R$ X fixos por mês?' — não altera os dados reais, é só um what-if."""
    st.markdown("#### 🎚️ Simulador: quanto poupar por mês?")

    simulated_monthly = st.slider(
        "Quanto você quer poupar por mês?",
        min_value=1000, max_value=10000, value=3000, step=100,
        key="savings_simulator_slider",
    )

    simulated_contributions = pd.Series([float(simulated_monthly)] * months_until_keys)
    simulated_portfolio_df = simulate_portfolio(
        contributions=simulated_contributions,
        months_until_keys=months_until_keys,
    )
    simulated_value_at_keys = (
        float(simulated_portfolio_df["Total Portfolio"].iloc[-1]) if not simulated_portfolio_df.empty else 0.0
    )
    simulated_gap = simulated_value_at_keys - renovation_cost

    c1, c2 = st.columns(2)
    c1.metric("Valor projetado nas chaves", money(simulated_value_at_keys))
    c2.metric("Gap simulado vs. reforma", money(simulated_gap))

    if simulated_gap >= 0:
        st.success(
            f"Com {money(simulated_monthly)}/mês, sua reforma fica coberta com folga de {money(simulated_gap)}."
        )
    else:
        st.warning(
            f"Com {money(simulated_monthly)}/mês, ainda falta {money(abs(simulated_gap))} para cobrir a reforma."
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

    evolution_start_month = st.number_input(
        "Mês de início da evolução da obra",
        min_value=1,
        max_value=profile.months_until_keys,
        value=3,
        help="Define a partir de qual mês a evolução da obra começa a impactar os custos.",
    )

    annual_installment = st.number_input(
        "Parcela anual opcional",
        min_value=0.0,
        value=0.0,
        step=500.0,
    )

    st.divider()

    st.subheader("Ajustes de estratégia")

    renovation_cash_ratio = st.slider(
        "Quanto da reforma você pagará à vista (%)",
        min_value=0.2,
        max_value=1.0,
        value=0.4,
        step=0.05
    )

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
    evolution_start_month=evolution_start_month,
    target_construction_evolution=profile.approved_first_installment,
)

real_data = load_real_data(construction_df)

renovation_df = estimate_renovation_cost(
    apartment_size_m2=profile.apartment_size_m2 or 50,
    package=renovation_package,
    months_until_keys=profile.months_until_keys,
    annual_inflation=annual_inflation,
    num_ares=num_ares,
)
renovation_cost = float(renovation_df["Inflated Cost"].sum())

# ============================
# TABS (criadas cedo de propósito: o data_editor da Controladoria precisa
# rodar e gravar no session_state ANTES do recálculo de portfólio/Monte Carlo
# logo abaixo — senão a edição só refletiria no próximo rerun do Streamlit)
# ============================
tab_control, tab_exec, tab_cashflow, tab_investments, tab_financing, tab_renovation, tab_decision, tab_risk, tab_data = st.tabs(
    [
        "📋 Controladoria",
        "📊 Geral",
        "🏗️ Fluxo de Obra",
        "💰 Investimentos",
        "🏦 Financiamento",
        "🛠️ Reforma",
        "🧠 Estratégia",
        "⚠️ Risco",
        "📁 Dados",
    ]
)

# ============================
# CONTROLADORIA MENSAL — PLANEJADO vs REAL (EDITÁVEL)
# ============================

months_list = [int(m) for m in construction_df["Month"].tolist()]

# Sincroniza/seeda o session_state. Se o perfil mudar (prazo diferente),
# os dicionários são resetados para os valores do modelo.
if "real_contributions" not in st.session_state or set(st.session_state.real_contributions.keys()) != set(months_list):
    st.session_state.real_contributions = {
        int(row["Month"]): float(row["Monthly Savings"])
        for _, row in construction_df.iterrows()
    }

if "real_evolution" not in st.session_state or set(st.session_state.real_evolution.keys()) != set(months_list):
    st.session_state.real_evolution = {
        int(row["Month"]): float(row["Construction Evolution"])
        for _, row in construction_df.iterrows()
    }

controladoria_df = pd.DataFrame({
    "Month": construction_df["Month"],
    "Planned Monthly Savings": construction_df["Monthly Savings"],
    "Real Monthly Savings": [st.session_state.real_contributions[m] for m in months_list],
    "Planned Construction Evolution": construction_df["Construction Evolution"],
    "Construction Evolution": [st.session_state.real_evolution[m] for m in months_list],
})

with tab_control:
    section(
        "Controladoria mensal",
        "Atualize mês a mês. O restante do app recalcula automaticamente.",
    )

    st.subheader("📊 Controle mensal (modo operacional)")

    # ==============================
    # PARÂMETROS
    # ==============================
    current_month = st.number_input(
        "Mês atual",
        min_value=1,
        max_value=len(construction_df),
        value=1,
        step=1
    )

    # ==============================
    # BASE
    # ==============================
    editable_df = construction_df.copy()

    editable_df["Month"] = construction_df["Month"]

    editable_df["Planned Savings"] = construction_df["Monthly Savings"]

    editable_df["Real Savings"] = [
        real_data.get(int(row["Month"]), {}).get("savings", float(row["Monthly Savings"]))
        for _, row in construction_df.iterrows()
    ]

    # ==============================
    # CONTROLAR EDIÇÃO
    # ==============================
    def is_editable(month):
        return month <= current_month

    editable_mask = editable_df["Month"].apply(is_editable)

    # ==============================
    # DATA EDITOR COM UX MELHOR
    # ==============================
    edited_df = st.data_editor(
        editable_df[["Month", "Planned Savings", "Real Savings"]],
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Month": st.column_config.NumberColumn("Mês", disabled=True),
            "Planned Savings": st.column_config.NumberColumn(
                "Planejado (R$)", disabled=True, format="R$ %.0f"
            ),
            "Real Savings": st.column_config.NumberColumn(
                "Real (R$)",
                format="R$ %.0f",
                step=100.0,
                min_value=0.0
            ),
        },
        key="control_editor"
    )

    # ==============================
    # SALVAR JSON
    # ==============================
    for _, row in edited_df.iterrows():
        month = int(row["Month"])

        if month <= current_month:
            if month not in real_data:
                real_data[month] = {}

            real_data[month]["savings"] = float(row["Real Savings"])

    save_real_data(real_data)

    # ==============================
    # MÉTRICAS OPERACIONAIS
    # ==============================
    real_series = pd.Series([
        real_data.get(int(row["Month"]), {}).get(
            "savings",
            float(row["Monthly Savings"])
        )
        for _, row in construction_df.iterrows()
    ])

    planned_total = construction_df["Monthly Savings"].cumsum()
    real_total = real_series.cumsum()

    gap_series = real_total - planned_total

    current_gap = gap_series.iloc[current_month - 1]

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Total planejado até agora",
        money(planned_total.iloc[current_month - 1])
    )

    c2.metric(
        "Total real",
        money(real_total.iloc[current_month - 1])
    )

    c3.metric(
        "Desvio do plano",
        money(current_gap),
        delta=money(current_gap)
    )

    # ==============================
    # STATUS DO PLANO
    # ==============================
    if current_gap < -3000:
        st.error("❌ Você está atrasado no plano — precisa compensar")
    elif current_gap < 0:
        st.warning("⚠️ Ligeiramente abaixo — monitorar")
    else:
        st.success("✅ Dentro ou acima do plano")

    # ==============================
    # MÉDIA REAL (INSIGHT)
    # ==============================
    avg_real = real_series.iloc[:current_month].mean()

    st.info(
        f"Média real até agora: {money(avg_real)} por mês"
    )

    # ==============================
    # FORECAST REAL (GAME CHANGER)
    # ==============================
    remaining_months = len(construction_df) - current_month

    forecast_total = real_total.iloc[current_month - 1] + avg_real * remaining_months

    st.subheader("🔮 Se continuar assim")

    st.metric(
        "Previsão de caixa nas chaves",
        money(forecast_total)
    )

    # ==============================
    # DECISÃO
    # ==============================
    effective_renovation_cash = renovation_cost * renovation_cash_ratio
    essential_need = effective_renovation_cash + (monthly_living_expenses * 6)

    forecast_gap = forecast_total - essential_need

    st.metric(
        "Folga prevista",
        money(forecast_gap)
    )

    if forecast_gap < 0:
        st.error(
            "❌ Nesse ritmo você NÃO chega → aumente a poupança"
        )
    elif forecast_gap < 10000:
        st.warning(
            "⚠️ Chega no limite → ideal aumentar um pouco"
        )
    else:
        st.success(
            "✅ Está confortável → pode manter estratégia"
        )


# Mantemos apenas os campos já calculados pelo modelo financeiro central.
construction_df["Poupança Gerada"] = construction_df["Monthly Savings"]
construction_df["Desembolso Real"] = construction_df["Real Monthly Spending"]

# ============================
# FEATURE 6: o resto do app usa SEMPRE real_contributions_series, nunca
# os valores planejados diretamente — isso já vale para portfolio_df, mc
# e (via projected_cash_at_keys) para o decision_engine logo abaixo.
# ============================
real_contributions_series = pd.Series([
    real_data.get(int(row["Month"]), {}).get("savings", float(row["Monthly Savings"]))
    for _, row in construction_df.iterrows()
])

portfolio_df = simulate_portfolio(
    contributions=real_contributions_series,
    months_until_keys=profile.months_until_keys,
)


mc = simulate_monte_carlo(
    monthly_contributions=real_contributions_series,
    months_until_keys=profile.months_until_keys,
    simulations=monte_carlo_runs,
)

amortization_df = generate_amortization_schedule(
    system=profile.financing_system,
    principal=profile.financing_ceiling,
    annual_rate=profile.annual_interest_rate,
    term_months=profile.term_months,
)


# Mantemos os pagamentos oficiais aprovados pela instituição financeira.
# O cronograma gerado pela modelagem técnica é preservado, mas os extremos
# do fluxo são sobrescritos para refletir os valores reais aprovados.
amortization_df.loc[0, "Payment"] = profile.approved_first_installment

if profile.approved_last_installment:
    amortization_df.loc[len(amortization_df) - 1, "Payment"] = profile.approved_last_installment


projected_cash_at_keys = float(portfolio_df["Total Portfolio"].iloc[-1])
total_contributed = float(portfolio_df["Total Contributed"].iloc[-1])
investment_gain = float(portfolio_df["Investment Gain"].iloc[-1])
renovation_cost = float(renovation_df["Inflated Cost"].sum())
renovation_coverage = projected_cash_at_keys / renovation_cost if renovation_cost else 0
gap = projected_cash_at_keys - renovation_cost


strategies_df = generate_decision_strategies(
    cash_at_keys=projected_cash_at_keys,
    renovation_cost=renovation_cost,
    monthly_expenses=monthly_living_expenses,
    outstanding_balance=profile.financing_ceiling,
    financing_annual_rate=profile.annual_interest_rate,
    financing_system=profile.financing_system,
    term_months=profile.term_months,
    investment_horizon_months=36,
    renovation_cash_ratio=renovation_cash_ratio,
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


with tab_exec:
    section(
        "Visão Executiva",
        "Próxima ação recomendada e resumo da posição financeira na entrega das chaves.",
    )

   
    st.subheader("Resumo financeiro real")

    # ======================
    # NECESSIDADE REAL
    # ======================
    effective_renovation_cash = renovation_cost * renovation_cash_ratio
    essential_need = effective_renovation_cash + (monthly_living_expenses * 6)

    gap = projected_cash_at_keys - essential_need

    c1, c2, c3 = st.columns(3)

    c1.metric("Caixa projetado", money(projected_cash_at_keys))
    c2.metric("Necessidade real", money(essential_need))
    c3.metric("Folga", money(gap))


    # ======================
    # TRAJETÓRIA REAL vs PLANO
    # ======================
    st.subheader("Acompanhamento do plano")

    planned_total = construction_df["Monthly Savings"].cumsum()
    real_total = real_contributions_series.cumsum()

    trajectory_gap = real_total - planned_total
    current_gap = trajectory_gap.iloc[-1]

    st.metric(
        "Desvio acumulado do plano",
        money(current_gap),
        delta=money(current_gap)
    )

    if current_gap < -5000:
        st.error("❌ Você está atrasado no plano")
    elif current_gap < 0:
        st.warning("⚠️ Ligeiramente abaixo do plano")
    else:
        st.success("✅ Dentro ou acima do plano")


    # ======================
    # FORECAST BASEADO NO REAL
    # ======================
    st.subheader("Se continuar assim...")

    avg_real_saving = real_contributions_series.mean()

    months_total = profile.months_until_keys
    months_done = len(real_contributions_series)
    remaining_months = months_total - months_done

    forecast_total = real_total.iloc[-1] + avg_real_saving * remaining_months
    forecast_gap = forecast_total - essential_need

    st.metric("Previsão nas chaves", money(forecast_total))
    st.metric("Folga prevista", money(forecast_gap))


    # ======================
    # DECISÃO REAL
    # ======================
    st.subheader("Próxima decisão")

    if forecast_gap < 0:
        st.error(
            "❌ Mantendo esse ritmo você NÃO chega. "
            "→ Aumente sua poupança mensal"
        )

    elif forecast_gap < monthly_living_expenses * 3:
        st.warning(
            "⚠️ Você chega no limite. "
            "→ Melhor aumentar um pouco a poupança"
        )

    else:
        st.success(
            "✅ Você está bem. "
            "→ Pode manter ou otimizar investimentos"
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

    st.divider()

    construction_display = construction_df.rename(columns={
        "Month": "Mês",
        "Builder Installment": "Prestação do construtor",
        "Construction Evolution": "Evolução da obra",
        "Annual Installment": "Parcela anual",
        "Total Cost": "Custo total",
        "Monthly Savings": "Poupança mensal",
        "Accumulated Savings": "Poupança acumulada",
        "Real Monthly Spending": "Gasto real mensal",
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
        }),
        use_container_width=True,
        hide_index=True,
    )


with tab_investments:
    section(
        "Investimentos",
        "Alocação dinâmica de portfólio conforme a entrega se aproxima.",
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

    st.markdown(explain_monte_carlo(mc))

    st.divider()
    render_savings_simulator(profile.months_until_keys, renovation_cost)

    st.divider()
    st.subheader("Onde investir este mês")

    available_months = construction_df["Month"].tolist()
    selected_month = st.selectbox(
        "Mês de referência", available_months,
        index=min(0, len(available_months) - 1),
    )

    allocation_this_month = get_current_allocation(portfolio_df, int(selected_month))

    # valor previsto
    contribution_this_month = float(
        construction_df.loc[
            construction_df["Month"] == selected_month, "Monthly Savings"
        ].iloc[0]
    )

    # valor REAL SALVO
    current_real_value = st.session_state.real_contributions.get(
        selected_month,
        contribution_this_month
    )


    # INPUT EDITÁVEL (com memória)
    monthly_investment_input = st.number_input(
        "💰 Este mês, você pretende investir:",
        min_value=0.0,
        value=current_real_value,
        step=100.0,
        key=f"investment_input_{selected_month}"
    )

    # salvar mudança
    st.session_state.real_contributions[selected_month] = monthly_investment_input

    # diferença vs modelo
    delta = monthly_investment_input - contribution_this_month

    st.caption(
        f"Previsto: {money(contribution_this_month)} | Diferença: {money(delta)}"
    )

    real_investment = monthly_investment_input


    # ========= LIQUIDEZ =========
    def calculate_redemption_month(month, asset_name, total_months):
        months_remaining = total_months - month

        if "Liquidez" in asset_name:
            return month
        elif "CDB" in asset_name:
            return month + 6 if months_remaining > 6 else month
        elif "LCI" in asset_name or "LCA" in asset_name:
            return month + 12 if months_remaining > 12 else month
        else:
            return month + 3 if months_remaining > 3 else month


    # tabela
    if allocation_this_month:
        alloc_table = pd.DataFrame([
            {
                "Ativo": asset_name,
                "Alocação": f"{weight * 100:.1f}%",
                "Valor (R$)": money(real_investment * weight),
                "Disponível no mês": calculate_redemption_month(
                    selected_month,
                    asset_name,
                    profile.months_until_keys
                )
            }
            for asset_name, weight in allocation_this_month.items()
        ])

        st.dataframe(alloc_table, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados de alocação para o mês selecionado.")


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
        hide_index=True)
    
    st.divider()
    st.subheader("Simulador de aporte extra")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        extra_payment = st.number_input(
            "Valor do aporte extra (R$)", min_value=0.0, value=0.0, step=1000.0,
        )
    with col_b:
        target_month = st.number_input(
            "Mês de aplicação do aporte", min_value=1,
            max_value=int(amortization_df["Month"].max()), value=1, step=1,
        )
    with col_c:
        mode_label = st.radio(
            "Objetivo do aporte",
            ["Reduzir prazo (recomendado)", "Reduzir parcela"],
        )
    mode = "reduce_term" if "prazo" in mode_label else "reduce_installment"

    if extra_payment > 0:
        result = simulate_extra_amortization(
            schedule=amortization_df,
            extra_payment=extra_payment,
            month=int(target_month),
            system=profile.financing_system,
            mode=mode,
        )

        c1, c2 = st.columns(2)
        c1.metric("Juros economizados", money(result["interest_saved"]))
        c2.metric("Meses reduzidos do contrato", f'{result["months_reduced"]} meses')

        if result["warning"]:
            st.warning(result["warning"])

        st.plotly_chart(
            amortization_chart(result["new_schedule"]),
            use_container_width=True,
            key="amortization_extra_chart",
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
        "Renovation (Cash Used)": "Reforma (à vista)",
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
        "Risco",
        "Espaço reservado para conteúdos de risco futuros.",
    )

    st.info("A aba de risco está pronta, mas o conteúdo será atualizado depois.")


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
    