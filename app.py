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
def converter_mes(mes_numero):
    """Traduz o número do mês (1 a 30) para o rótulo real (Jul/2026 a Dez/2028)"""
    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    idx = int(mes_numero) - 1
    mes_nome = meses[(6 + idx) % 12]  # 6 representa Julho (índice 6)
    ano = 2026 + ((6 + idx) // 12)
    return f"{mes_nome}/{ano}"

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

# ============================
# CONTROLADORIA MENSAL — SINCRONIZADA COM NOTION
# ============================

with tab_control:
    st.subheader("📋 Controladoria (Sincronizada com Notion)")
    
    try:
        from notion_integration import fetch_notion_data, recalculate_forecast
        import plotly.express as px
        
        # 1. Puxa os dados da API (Lendo do seu secrets.toml)
        df_bruto = fetch_notion_data(
            notion_token=st.secrets["NOTION_TOKEN"],
            database_id=st.secrets["NOTION_DATABASE_ID"]
        )
        
        # 2. Roda a inteligência financeira (GAP de 14.600 e Aporte de 6.000)
        df_controle = recalculate_forecast(
            df=df_bruto,
            gap_inicial=14600.0,
            aporte_padrao=6000.0
        )
        
        # 3. Visão Facilitada (Cards Superiores)
        total_eo_geral = df_controle['Evolução de Obra (R$)'].sum()
        total_poupanca_geral = df_controle['Poupança Gerada (R$)'].sum()
        total_esforco_caixa = df_controle['Desembolso Real do Mês (R$)'].sum()

        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("💰 1. Poupança Acumulada", money(total_poupanca_geral), "Seu poder de fogo")
        col_t2.metric("2. Total de Evol. de Obra (EO)", money(total_eo_geral))
        col_t3.metric("3. Esforço Total de Caixa", money(total_esforco_caixa))

        st.divider()

        # 4. Gráfico Empilhado (Exclusivo da Controladoria)
        st.markdown("### Composição Mensal e Alertas de Risco")
        
        # Aplica a conversão de datas no Eixo X
        df_controle['Mês Formatado'] = df_controle['Mês'].apply(converter_mes)
        
        # INCLUÍMOS 'Amortização' na lista de Y e definimos as cores
        fig = px.bar(
            df_controle, 
            x='Mês Formatado', 
            y=[
                'Parcela Construtora (R$)', 
                'Amortização', 
                'Poupança Gerada (R$)', 
                'Evolução de Obra (R$)'
            ],
            labels={'value': 'Orçamento Mensal (R$)', 'variable': 'Composição', 'Mês Formatado': 'Mês'},
            color_discrete_map={
                'Parcela Construtora (R$)': '#1f77b4',  # Azul
                'Amortização': '#9B59B6',               # Roxo (para diferenciar)
                'Poupança Gerada (R$)': '#2ca02c',      # Verde
                'Evolução de Obra (R$)': '#ff7f0e'      # Laranja
            }
        )
        
        # 1. Cria a coluna de soma explícita para o total
        df_controle["Total do Mês (Custo)"] = (
            df_controle['Parcela Construtora (R$)'] + 
            df_controle['Amortização'] + 
            df_controle['Poupança Gerada (R$)'] + 
            df_controle['Evolução de Obra (R$)']
        )
        
        renda_casal = profile.household_income
        fig.add_hline(y=renda_casal * 0.30, line_dash="dash", line_color="gold", annotation_text="⚠️ 30% da Renda")
        fig.add_hline(y=renda_casal * 0.50, line_dash="dash", line_color="red", annotation_text="🚨 50% da Renda")

        # 2. O HACK: Adiciona a linha invisível que força o tooltip a mostrar o total
        fig.add_scatter(
            x=df_controle['Mês Formatado'], 
            y=df_controle["Total do Mês (Custo)"],
            mode='lines', 
            line=dict(color='rgba(0,0,0,0)'), # Invisível
            name='Total do Mês (Custo)',
            hovertemplate="<b>Total do Mês (Custo) : R$ %{y:,.2f}</b>"
        )
        
        # O hovermode="x unified" agora somará as 4 colunas automaticamente no total
        fig.update_layout(
            barmode='stack', 
            legend_title_text='', 
            xaxis_title="Cronograma até as Chaves",
            hovermode="x unified",
            hoverlabel=dict(bgcolor="#1E1E1E", font_size=14, font_family="sans-serif")
        )
        fig.update_traces(hovertemplate="<b>R$ %{y:,.2f}</b>", selector=dict(type='bar'))
        st.plotly_chart(fig, use_container_width=True)

        # =====================================================================
        # SIMULADOR DE AMORTIZAÇÃO DA CONSTRUTORA (TIRO CURTO)
        # =====================================================================
        st.divider()
        st.markdown("### 🎯 Simulador de Amortização (Construtora)")
        st.caption("Simule o impacto de usar sua Poupança Acumulada para aniquilar as parcelas da construtora de trás pra frente.")

        # 1. Descobre a munição atual (Poupança Acumulada do último mês fechado)
        meses_fechados = df_controle[df_controle["Status"] == "Fechado"]
        if not meses_fechados.empty:
            poupanca_disponivel = meses_fechados["Poupança Acumulada (R$)"].iloc[-1]
            pago_construtora = meses_fechados["Parcela Construtora (R$)"].sum()
        else:
            poupanca_disponivel = df_controle["Poupança Acumulada (R$)"].iloc[0]
            pago_construtora = 0.0

        # 2. Descobre a dívida atual com a construtora
        saldo_devedor_atual = max(14600.00 - pago_construtora, 0.0)

        # 3. Descobre o valor da parcela que será eliminada (média das projetadas)
        meses_projetados = df_controle[df_controle["Status"] == "Projetado"]
        if not meses_projetados.empty:
            parcela_alvo = meses_projetados["Parcela Construtora (R$)"].iloc[0]
        else:
            parcela_alvo = 528.08 # Fallback de segurança

        # Interface do Simulador
        col_sim1, col_sim2 = st.columns([1, 1])
        with col_sim1:
            aporte_simulado = st.number_input(
                "Valor do aporte extra (R$)",
                min_value=0.0,
                max_value=float(poupanca_disponivel),
                value=0.0,
                step=500.0,
                help="O valor máximo permitido é a sua Poupança Acumulada atual."
            )
        with col_sim2:
            st.info(f"**Saldo Devedor Atual:** R$ {saldo_devedor_atual:,.2f}\n\n**Munição Disponível:** R$ {poupanca_disponivel:,.2f}")

        # Motor de Recálculo do Simulador
        if aporte_simulado > 0:
            if parcela_alvo > 0:
                meses_atuais_restantes = saldo_devedor_atual / parcela_alvo
                novo_saldo_devedor = max(saldo_devedor_atual - aporte_simulado, 0.0)
                novos_meses_restantes = novo_saldo_devedor / parcela_alvo
                meses_eliminados = meses_atuais_restantes - novos_meses_restantes
            else:
                meses_eliminados = 0
                novo_saldo_devedor = 0
                novos_meses_restantes = 0

            st.success(f"🔥 Impacto de injetar **R$ {aporte_simulado:,.2f}** hoje:")
            
            c_res1, c_res2, c_res3 = st.columns(3)
            c_res1.metric("Parcelas Eliminadas", f"{int(meses_eliminados)} meses", "De trás pra frente")
            c_res2.metric("Novo Saldo Devedor", f"R$ {novo_saldo_devedor:,.2f}")
            c_res3.metric("Prazo Restante", f"{int(novos_meses_restantes)} meses")
            
            st.caption(f"*Nota: Ao eliminar {int(meses_eliminados)} meses de construtora, a sua sobra de caixa de R$ 6.000,00 mensais nesses meses finais poderá ser 100% direcionada para absorver a Evolução de Obra ou engordar o Caixa do Imóvel.*")

        # =====================================================================
        # INTEGRAÇÃO PROFUNDA: Substituindo os dados teóricos pelos reais do Notion
        # =====================================================================
        limit = min(len(df_controle), len(construction_df))
        
        construction_df.loc[:limit-1, "Builder Installment"] = df_controle["Parcela Construtora (R$)"].iloc[:limit].values
        construction_df.loc[:limit-1, "Construction Evolution"] = df_controle["Evolução de Obra (R$)"].iloc[:limit].values
        construction_df.loc[:limit-1, "Monthly Savings"] = df_controle["Poupança Gerada (R$)"].iloc[:limit].values
        construction_df.loc[:limit-1, "Real Monthly Spending"] = df_controle["Desembolso Real do Mês (R$)"].iloc[:limit].values
        
        # NOVA LINHA: Puxa a amortização do Notion para a base do app
        construction_df.loc[:limit-1, "Amortização"] = df_controle["Amortização"].iloc[:limit].values
        
        # CORREÇÃO DO MISTÉRIO: Obriga o app a recalcular a poupança acumulada baseada nos valores reais
        construction_df["Accumulated Savings"] = construction_df["Monthly Savings"].cumsum()
        
        # Alimenta o motor de investimentos e risco com a sua poupança real
        real_contributions_series = df_controle["Poupança Gerada (R$)"].iloc[:limit]

        # RECRIA O ESTADO DE SESSÃO PARA A ABA DE INVESTIMENTOS NÃO QUEBRAR
        if "real_contributions" not in st.session_state:
            st.session_state.real_contributions = {}
        for m, val in zip(df_controle["Mês"], df_controle["Poupança Gerada (R$)"]):
            st.session_state.real_contributions[int(m)] = float(val)

    except Exception as e:
        st.error(f"Erro de conexão com o Notion ou processamento de dados.")
        st.info("Verifique se o arquivo 'notion_integration.py' está na mesma pasta e se o 'secrets.toml' está preenchido corretamente.")
        st.code(str(e))
        st.stop()

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

    # 1. Gráfico com meses formatados
    df_grafico = construction_df.copy()
    df_grafico["Month"] = df_grafico["Month"].apply(converter_mes)

    st.plotly_chart(
        cashflow_stacked_chart(df_grafico, renda=profile.household_income),
        use_container_width=True,
        key="cashflow_chart"
    )

    st.divider()

    # 2. Tabela com meses formatados
    construction_display = construction_df.copy()
    
    if "Amortização" not in construction_display.columns:
        construction_display["Amortização"] = 0.0
    construction_display["Amortização"] = construction_display["Amortização"].fillna(0)
    
    construction_display["Aporte Casal"] = construction_display["Real Monthly Spending"] + construction_display["Monthly Savings"]
    
    construction_display = construction_display.rename(columns={
        "Month": "Mês",
        "Builder Installment": "Prestação Construtora",
        "Amortização": "Amortização",
        "Construction Evolution": "Evolução de Obra (EO)",
        "Real Monthly Spending": "Custo Total",
        "Monthly Savings": "Poupança Mensal",
        "Accumulated Savings": "Poupança Acumulada",
    })

    col_order = [
        "Mês",
        "Prestação Construtora",
        "Amortização",
        "Evolução de Obra (EO)",
        "Custo Total",
        "Aporte Casal",
        "Poupança Mensal",
        "Poupança Acumulada"
    ]

    df_formatado = construction_display[col_order].copy()
    
    # Formatação condicional: se for o Mês aplica a data, senão aplica os R$
    for col in df_formatado.columns:
        if col == "Mês":
            df_formatado[col] = df_formatado[col].apply(converter_mes)
        else:
            df_formatado[col] = df_formatado[col].apply(
                lambda x: f"R$ {float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )

    st.dataframe(
        df_formatado,
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
    construction_data_display = construction_df.drop(columns=["Stress Amount", "Stress Ratio"]).rename(columns={
        "Month": "Mês",
        "Builder Installment": "Prestação do construtor",
        "Construction Evolution": "Evolução da obra",
        "Annual Installment": "Parcela anual",
        "Total Cost": "Custo total",
        "Monthly Savings": "Poupança mensal",
        "Accumulated Savings": "Poupança acumulada",
        "Real Monthly Spending": "Gasto real mensal",
    })
    st.dataframe(construction_data_display, use_container_width=True, hide_index=True)

    st.subheader("Portfólio")
    portfolio_data_display = portfolio_df.rename(columns={
        "Month": "Mês",
        "Contribution": "Contribuição",
        "Total Portfolio": "Total do portfólio",
        "Total Contributed": "Total contribuído",
        "Investment Gain": "Ganho do investimento",
    })
    st.dataframe(portfolio_data_display, use_container_width=True, hide_index=True)

    st.subheader("Reforma")
    renovation_data_display = renovation_df.rename(columns={
        "Category": "Categoria",
        "Base Cost": "Custo base",
        "Inflated Cost": "Custo inflado",
        "Cost per m²": "Custo por m²",
        "Share": "Participação",
    })
    st.dataframe(renovation_data_display, use_container_width=True, hide_index=True)

    st.subheader("Estratégias de decisão")
    strategies_data_display = strategies_df.rename(columns={
        "Strategy": "Estratégia",
        "Emergency Reserve": "Reserva de emergência",
        "Renovation (Cash Used)": "Reforma (caixa usada)",
        "Total Renovation Cost": "Custo total da reforma",
        "Loan Amortization": "Amortização do empréstimo",
        "Idle Cash": "Caixa ocioso",
        "Interest Saved": "Juros economizados",
        "Investment Alternative": "Alternativa de investimento",
        "Advantage": "Vantagem",
    })
    st.dataframe(strategies_data_display, use_container_width=True, hide_index=True)
    