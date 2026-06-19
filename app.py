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
    page_title="Brazil Real Estate Financial Planner",
    page_icon="🏢",
    layout="wide",
)

apply_global_styles()


st.title("🏢 Real Estate Financial Planning Cockpit")
st.caption(
    "Enterprise-grade decision engine for Brazilian off-plan apartment buyers."
)


with st.sidebar:
    st.header("Planning Inputs")

    selected_profile_name = st.selectbox(
        "Buyer profile",
        list(PROFILES.keys()),
        help="Choose a predefined real buyer profile.",
    )

    profile = PROFILES[selected_profile_name]

    st.divider()

    monthly_budget = st.number_input(
        "Total monthly budget during construction",
        min_value=0.0,
        value=float(4_000 if profile.name == "Vinicius & Ju" else 1_500),
        step=100.0,
        help="Total amount available every month for construction costs and savings.",
    )

    minimum_saving_floor = st.number_input(
        "Minimum monthly saving floor",
        min_value=0.0,
        value=float(1_000 if profile.name == "Vinicius & Ju" else 300),
        step=100.0,
        help="Minimum savings forced every month even if spending exceeds the budget.",
    )

    construction_curve = st.selectbox(
        "Construction evolution curve",
        ["Linear", "S-Curve", "Back-loaded"],
        index=1,
        help="Controls how construction evolution grows until keys.",
    )

    annual_installment = st.number_input(
        "Optional annual installment",
        min_value=0.0,
        value=0.0,
        step=500.0,
    )

    st.divider()

    renovation_package = st.selectbox(
        "Renovation package",
        ["Basic", "Recommended", "Premium"],
        index=1,
    )

    annual_inflation = st.number_input(
        "Renovation annual inflation",
        min_value=0.0,
        value=0.045,
        step=0.005,
        format="%.3f",
    )

    monthly_living_expenses = st.number_input(
        "Estimated monthly living expenses after keys",
        min_value=0.0,
        value=float(profile.household_income * 0.55),
        step=100.0,
        help="Used to calculate emergency reserve requirements.",
    )

    monte_carlo_runs = st.slider(
        "Monte Carlo simulations",
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
)

amortization_df = generate_amortization_schedule(
    system=profile.financing_system,
    principal=profile.financing_ceiling,
    annual_rate=profile.annual_interest_rate,
    term_months=profile.term_months,
)

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


tab_cockpit, tab_cashflow, tab_investments, tab_financing, tab_renovation, tab_decision, tab_risk, tab_data = st.tabs(
    [
        "Cockpit",
        "Construction Cash Flow",
        "Investments",
        "Financing",
        "Renovation",
        "Decision Engine",
        "Risk",
        "Data",
    ]
)


with tab_cockpit:
    section(
        "Executive Cockpit",
        "High-level financial position at keys and decision readiness.",
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Projected cash at keys",
        money(projected_cash_at_keys),
        help="Projected investment portfolio value at keys.",
    )

    c2.metric(
        "Investment gain",
        money(investment_gain),
        help="Portfolio value minus total contributions.",
    )

    c3.metric(
        "Renovation coverage",
        pct(renovation_coverage),
        help="Cash at keys divided by projected renovation cost.",
    )

    c4.metric(
        "Risk score",
        f'{risk["overall"]["score"]}/100',
        status_badge(risk["overall"]["status"]),
    )

    st.divider()

    c5, c6, c7 = st.columns(3)

    c5.metric("Peak stress month", f"Month {peak_stress_month}")
    c6.metric("Best strategy", best_strategy["Strategy"])
    c7.metric("Monte Carlo P50", money(mc["p50"]))

    st.info(
        f"""
        Recommended strategy: **{best_strategy["Strategy"]}**.

        This strategy allocates approximately:
        - {money(best_strategy["Emergency Reserve"])} to emergency reserve
        - {money(best_strategy["Renovation"])} to renovation
        - {money(best_strategy["Loan Amortization"])} to loan amortization
        """
    )

    st.plotly_chart(portfolio_composition_chart(portfolio_df), use_container_width=True)
    st.plotly_chart(risk_heatmap(risk), use_container_width=True)


with tab_cashflow:
    section(
        "Construction Phase Cash Flow",
        "Tracks monthly construction evolution, forced savings, spending pressure, and accumulated savings.",
    )

    st.plotly_chart(cashflow_stacked_chart(construction_df), use_container_width=True)

    st.dataframe(
        construction_df.style.format({
            "Builder Installment": "R$ {:,.2f}",
            "Construction Evolution": "R$ {:,.2f}",
            "Annual Installment": "R$ {:,.2f}",
            "Total Cost": "R$ {:,.2f}",
            "Monthly Savings": "R$ {:,.2f}",
            "Accumulated Savings": "R$ {:,.2f}",
            "Real Monthly Spending": "R$ {:,.2f}",
            "Stress Amount": "R$ {:,.2f}",
            "Stress Ratio": "{:.2f}",
        }),
        use_container_width=True,
    )


with tab_investments:
    section(
        "Investment Engine",
        "Dynamic glide-path allocation from balanced risk to ultra-conservative as keys approach.",
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Total contributed", money(total_contributed))
    c2.metric("Expected portfolio", money(projected_cash_at_keys))
    c3.metric("Expected gain", money(investment_gain))

    st.plotly_chart(portfolio_composition_chart(portfolio_df), use_container_width=True)

    st.subheader("Monte Carlo Simulation")
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
    )


with tab_financing:
    section(
        "Financing Engine",
        f"Full amortization table using {profile.financing_system}.",
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Principal", money(profile.financing_ceiling))
    c2.metric("Annual rate", pct(profile.annual_interest_rate))
    c3.metric("Term", f"{profile.term_months} months")
    c4.metric("First installment", money(amortization_df["Payment"].iloc[0]))

    st.plotly_chart(amortization_chart(amortization_df), use_container_width=True)

    st.dataframe(
        amortization_df.style.format({
            "Opening Balance": "R$ {:,.2f}",
            "Interest": "R$ {:,.2f}",
            "Amortization": "R$ {:,.2f}",
            "Payment": "R$ {:,.2f}",
            "Ending Balance": "R$ {:,.2f}",
        }),
        use_container_width=True,
    )


with tab_renovation:
    section(
        "Renovation and Furniture Engine",
        "Inflation-adjusted estimate by cost category and selected package.",
    )

    c1, c2 = st.columns(2)
    c1.metric("Projected renovation cost", money(renovation_cost))
    c2.metric("Package", renovation_package)

    st.plotly_chart(renovation_pie_chart(renovation_df), use_container_width=True)

    st.dataframe(
        renovation_df.style.format({
            "Base Cost": "R$ {:,.2f}",
            "Inflated Cost": "R$ {:,.2f}",
            "Cost per m²": "R$ {:,.2f}",
            "Share": "{:.1%}",
        }),
        use_container_width=True,
    )


with tab_decision:
    section(
        "Decision Engine at Keys",
        "Ranks allocation strategies across renovation, emergency reserve, and loan amortization.",
    )

    st.plotly_chart(strategy_score_chart(strategies_df), use_container_width=True)

    st.dataframe(
        strategies_df.style.format({
            "Emergency Reserve": "R$ {:,.2f}",
            "Renovation": "R$ {:,.2f}",
            "Loan Amortization": "R$ {:,.2f}",
            "Idle Cash": "R$ {:,.2f}",
            "Renovation Coverage": "{:.1%}",
            "Reserve Months": "{:.1f}",
            "Financial Score": "{:.1f}",
            "Safety Score": "{:.1f}",
            "Quality of Life Score": "{:.1f}",
            "Total Score": "{:.1f}",
        }),
        use_container_width=True,
    )


with tab_risk:
    section(
        "Risk Scoring System",
        "Combines income commitment, savings stress, and renovation coverage into a 0-100 score.",
    )

    st.plotly_chart(risk_heatmap(risk), use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Income commitment",
        pct(risk["income_commitment"]["ratio"]),
        status_badge(risk["income_commitment"]["status"]),
    )

    c2.metric(
        "Savings stress",
        f'{risk["savings_stress"]["score"]:.1f}/100',
        status_badge(risk["savings_stress"]["status"]),
    )

    c3.metric(
        "Renovation coverage",
        pct(risk["renovation_coverage"]["coverage"]),
        status_badge(risk["renovation_coverage"]["status"]),
    )

    c4.metric(
        "Overall risk",
        f'{risk["overall"]["score"]:.1f}/100',
        status_badge(risk["overall"]["status"]),
    )


with tab_data:
    section(
        "Model Data",
        "Raw outputs for validation, auditability, and export.",
    )

    st.subheader("Selected Profile")
    st.json(profile.__dict__)

    st.subheader("Construction Cash Flow")
    st.dataframe(construction_df, use_container_width=True)

    st.subheader("Portfolio")
    st.dataframe(portfolio_df, use_container_width=True)

    st.subheader("Renovation")
    st.dataframe(renovation_df, use_container_width=True)

    st.subheader("Decision Strategies")
    st.dataframe(strategies_df, use_container_width=True)