import math
import numpy as np
import pandas as pd

from finance.amortization import generate_amortization_schedule
from investments.allocation import dynamic_allocation
from core.constants import ASSETS


def _interest_saved_by_amortization(
    loan_amortization: float,
    outstanding_balance: float,
    financing_annual_rate: float,
    financing_system: str,
    term_months: int,
) -> float:
    """Juros economizados ao amortizar `loan_amortization` agora, simulando
    o cronograma real (mesmo sistema, mesma taxa, mesmo prazo) com e sem o aporte."""
    if loan_amortization <= 0 or outstanding_balance <= 0 or term_months <= 0:
        return 0.0

    baseline = generate_amortization_schedule(
        financing_system, outstanding_balance, financing_annual_rate, term_months
    )
    baseline_interest = float(baseline["Interest"].sum())

    reduced_principal = max(outstanding_balance - loan_amortization, 0.0)
    if reduced_principal <= 0:
        return baseline_interest

    reduced = generate_amortization_schedule(
        financing_system, reduced_principal, financing_annual_rate, term_months
    )
    reduced_interest = float(reduced["Interest"].sum())

    return max(baseline_interest - reduced_interest, 0.0)


def _blended_after_tax_monthly_return(amount: float, horizon_months: int) -> float:
    """Retorno mensal líquido médio (após IR) ponderado pela alocação dinâmica
    apropriada para o horizonte informado."""
    if amount <= 0:
        return 0.0

    allocation = dynamic_allocation(months_remaining=horizon_months, monthly_contribution=amount)

    blended = 0.0
    for asset_key, weight in allocation.items():
        asset = ASSETS[asset_key]
        gross_monthly = (1 + asset.annual_return) ** (1 / 12) - 1
        after_tax_monthly = gross_monthly * (1 - asset.tax_rate)
        blended += weight * after_tax_monthly

    return blended


def _investment_gain_if_invested(amount: float, horizon_months: int) -> float:
    """Ganho esperado (R$) se `amount` fosse investido em vez de usado para amortizar."""
    if amount <= 0 or horizon_months <= 0:
        return 0.0

    r = _blended_after_tax_monthly_return(amount, horizon_months)
    future_value = amount * (1 + r) ** horizon_months
    return future_value - amount


def generate_decision_strategies(
    cash_at_keys: float,
    renovation_cost: float,
    monthly_expenses: float,
    outstanding_balance: float,
    financing_annual_rate: float,
    financing_system: str = "SAC",
    term_months: int = 360,
    investment_horizon_months: int = 36,
) -> pd.DataFrame:
    """
    Aloca o caixa disponível nas chaves entre reforma, reserva de emergência
    e amortização do financiamento, e compara o ganho financeiro REAL de
    amortizar vs. investir o mesmo valor (em R$, não em score abstrato).
    """

    emergency_targets = {
        "Aggressive Amortization": 3,
        "Balanced": 6,
        "Safety First": 9,
        "Quality of Life": 6,
    }

    renovation_targets = {
        "Aggressive Amortization": 0.70,
        "Balanced": 1.00,
        "Safety First": 0.75,
        "Quality of Life": 1.15,
    }

    amortization_bias = {
        "Aggressive Amortization": 0.80,
        "Balanced": 0.50,
        "Safety First": 0.20,
        "Quality of Life": 0.25,
    }

    rows = []

    for strategy in emergency_targets:
        emergency_reserve = min(
            emergency_targets[strategy] * monthly_expenses,
            cash_at_keys,
        )

        remaining_after_reserve = max(cash_at_keys - emergency_reserve, 0)

        renovation_allocation = min(
            renovation_cost * renovation_targets[strategy],
            remaining_after_reserve,
        )

        remaining_after_renovation = max(
            remaining_after_reserve - renovation_allocation,
            0,
        )

        loan_amortization = min(
            remaining_after_renovation * amortization_bias[strategy],
            outstanding_balance,
        )

        idle_cash = max(
            remaining_after_renovation - loan_amortization,
            0,
        )

        renovation_coverage = (
            renovation_allocation / renovation_cost if renovation_cost > 0 else 1
        )

        reserve_coverage_months = (
            emergency_reserve / monthly_expenses if monthly_expenses > 0 else 0
        )

        # --- Comparação financeira REAL (substitui o score quebrado) ---
        interest_saved = _interest_saved_by_amortization(
            loan_amortization, outstanding_balance, financing_annual_rate,
            financing_system, term_months,
        )
        investment_gain_alt = _investment_gain_if_invested(
            loan_amortization, investment_horizon_months,
        )
        net_financial_advantage = interest_saved - investment_gain_alt

        # Score 0-100 normalizado pela própria vantagem em R$ (limitado, não satura sozinho)
        ratio = net_financial_advantage / cash_at_keys if cash_at_keys > 0 else 0.0
        financial_score = float(np.clip(50 + ratio * 500, 0, 100))

        safety_score = min(100, reserve_coverage_months / 6 * 100)
        qol_score = min(100, renovation_coverage * 100)

        total_score = (
            financial_score * 0.40
            + safety_score * 0.35
            + qol_score * 0.25
        )

        rows.append({
            "Strategy": strategy,
            "Emergency Reserve": emergency_reserve,
            "Renovation": renovation_allocation,
            "Loan Amortization": loan_amortization,
            "Idle Cash": idle_cash,
            "Renovation Coverage": renovation_coverage,
            "Reserve Months": reserve_coverage_months,
            "Interest Saved (Amortization)": interest_saved,
            "Investment Return Expected (Alternative)": investment_gain_alt,
            "Net Financial Advantage": net_financial_advantage,
            "Financial Score": financial_score,
            "Safety Score": safety_score,
            "Quality of Life Score": qol_score,
            "Total Score": total_score,
        })

    df = pd.DataFrame(rows)
    return df.sort_values("Total Score", ascending=False).reset_index(drop=True)