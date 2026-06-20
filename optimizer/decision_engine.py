import numpy as np
import pandas as pd

from finance.amortization import generate_amortization_schedule
from investments.allocation import dynamic_allocation
from core.constants import ASSETS


def _interest_saved_by_amortization(
    loan_amortization,
    outstanding_balance,
    financing_annual_rate,
    financing_system,
    term_months,
):
    if loan_amortization <= 0:
        return 0

    baseline = generate_amortization_schedule(
        financing_system,
        outstanding_balance,
        financing_annual_rate,
        term_months,
    )

    reduced = generate_amortization_schedule(
        financing_system,
        max(outstanding_balance - loan_amortization, 0),
        financing_annual_rate,
        term_months,
    )

    return baseline["Interest"].sum() - reduced["Interest"].sum()


def _investment_gain(amount, months):
    if amount <= 0:
        return 0

    allocation = dynamic_allocation(months, amount)

    total_return = 0

    for asset_key, weight in allocation.items():
        asset = ASSETS[asset_key]

        monthly_return = (1 + asset.annual_return) ** (1 / 12) - 1
        after_tax = monthly_return * (1 - asset.tax_rate)

        total_return += weight * after_tax

    future_value = amount * (1 + total_return) ** months

    return future_value - amount


def generate_decision_strategies(
    cash_at_keys,
    renovation_cost,
    monthly_expenses,
    outstanding_balance,
    financing_annual_rate,
    financing_system="SAC",
    term_months=360,
    investment_horizon_months=36,
    renovation_cash_ratio=0.4  # 🔥 NOVO
):
    """
    Agora:
    - reforma NÃO consome 100% do caixa
    - parte é parcelada / flexível
    """

    strategies = {
        "Aggressive Amortization": (3, 0.7, 0.8),
        "Balanced": (6, 1.0, 0.5),
        "Safety First": (9, 0.75, 0.2),
        "Quality of Life": (6, 1.15, 0.25),
    }

    rows = []

    for name, (reserve_m, reno_factor, amort_factor) in strategies.items():

        # ============================
        # 1. RESERVA
        # ============================
        max_reserve = reserve_m * monthly_expenses

        # 🔥 limite de reserva como % do caixa
        reserve_cap = 0.6  # no máximo 60% do caixa

        reserve = min(
            max_reserve,
            cash_at_keys * reserve_cap
        )

        remaining = cash_at_keys - reserve

        # ============================
        # 2. REFORMA (CORREÇÃO)
        # ============================

        # 🔥 só parte da reforma precisa ser paga à vista
        effective_renovation_cost = renovation_cost * renovation_cash_ratio

        
        renovation = min(
            effective_renovation_cost * min(reno_factor, 1.0),
            remaining
        )


        remaining -= renovation

        # ============================
        # 3. AMORTIZAÇÃO VS INVESTIMENTO
        # ============================

        # garantir que sempre existe material para decisão

        min_base = cash_at_keys * 0.10  # 🔥 10% do caixa disponível

        usable_cash = max(remaining, min_base)

        amortization = min(
            usable_cash * amort_factor,
            outstanding_balance
        )

        idle = max(remaining - amortization, 0)

        # ============================
        # 4. GANHO REAL
        # ============================

        interest_saved = _interest_saved_by_amortization(
            amortization,
            outstanding_balance,
            financing_annual_rate,
            financing_system,
            term_months,
        )

        invest_gain = _investment_gain(
            amortization,
            investment_horizon_months
        )

        advantage = interest_saved - invest_gain

        rows.append({
            "Strategy": name,
            "Emergency Reserve": reserve,
            "Renovation (Cash Used)": renovation,
            "Total Renovation Cost": renovation_cost,
            "Loan Amortization": amortization,
            "Idle Cash": idle,
            "Interest Saved": interest_saved,
            "Investment Alternative": invest_gain,
            "Advantage": advantage,
        })

    df = pd.DataFrame(rows)

    return df.sort_values("Advantage", ascending=False)
