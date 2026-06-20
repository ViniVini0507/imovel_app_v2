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
):
    strategies = {
        "Aggressive Amortization": (3, 0.7, 0.8),
        "Balanced": (6, 1.0, 0.5),
        "Safety First": (9, 0.75, 0.2),
        "Quality of Life": (6, 1.15, 0.25),
    }

    rows = []

    for name, (reserve_m, reno_factor, amort_factor) in strategies.items():

        reserve = min(reserve_m * monthly_expenses, cash_at_keys)

        remaining = cash_at_keys - reserve

        renovation = min(renovation_cost * reno_factor, remaining)

        remaining -= renovation

        amortization = min(remaining * amort_factor, outstanding_balance)

        idle = remaining - amortization

        interest_saved = _interest_saved_by_amortization(
            amortization,
            outstanding_balance,
            financing_annual_rate,
            financing_system,
            term_months,
        )

        invest_gain = _investment_gain(amortization, investment_horizon_months)

        advantage = interest_saved - invest_gain

        rows.append({
            "Strategy": name,
            "Emergency Reserve": reserve,
            "Renovation": renovation,
            "Loan Amortization": amortization,
            "Idle Cash": idle,
            "Interest Saved": interest_saved,
            "Investment Alternative": invest_gain,
            "Advantage": advantage,
        })

    df = pd.DataFrame(rows)

    return df.sort_values("Advantage", ascending=False)