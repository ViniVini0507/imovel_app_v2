import pandas as pd


def generate_decision_strategies(
    cash_at_keys: float,
    renovation_cost: float,
    monthly_expenses: float,
    outstanding_balance: float,
    financing_annual_rate: float,
) -> pd.DataFrame:
    """
    Allocates cash among:
    - renovation
    - emergency reserve
    - loan amortization

    Scores:
    - financial optimization
    - safety/liquidity
    - quality of life
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
            renovation_allocation / renovation_cost
            if renovation_cost > 0
            else 1
        )

        reserve_coverage_months = (
            emergency_reserve / monthly_expenses
            if monthly_expenses > 0
            else 0
        )

        financial_score = min(
            100,
            45
            + 300 * (loan_amortization / outstanding_balance if outstanding_balance > 0 else 0)
            + 80 * financing_annual_rate,
        )

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
            "Financial Score": financial_score,
            "Safety Score": safety_score,
            "Quality of Life Score": qol_score,
            "Total Score": total_score,
        })

    df = pd.DataFrame(rows)
    return df.sort_values("Total Score", ascending=False).reset_index(drop=True)