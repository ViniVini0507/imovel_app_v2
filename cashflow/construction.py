import numpy as np
import pandas as pd


def construction_evolution_curve(
    months: int,
    initial_value: float,
    curve_type: str,
    final_multiplier: float = 5.5,
    start_month: int = 1
):
    """
    Generates construction evolution curve with delayed start.

    start_month:
    - month when evolution actually begins
    - before that → evolution = 0
    """

    x = np.linspace(0, 1, months)

    # curva base
    if curve_type == "Linear":
        factors = 1 + (final_multiplier - 1) * x

    elif curve_type == "S-Curve":
        sigmoid = 1 / (1 + np.exp(-10 * (x - 0.5)))
        normalized = (sigmoid - sigmoid.min()) / (sigmoid.max() - sigmoid.min())
        factors = 1 + (final_multiplier - 1) * normalized

    elif curve_type == "Back-loaded":
        factors = 1 + (final_multiplier - 1) * (x ** 2.2)

    else:
        raise ValueError("Unknown curve type")

    values = initial_value * factors

    # ✅ AQUI ESTÁ O AJUSTE (início só depois)
    evolution = []

    for i in range(months):
        if i + 1 < start_month:
            evolution.append(0)
        else:
            evolution.append(values[i - start_month + 1])

    return np.array(evolution)


def simulate_construction_phase(
    months: int,
    builder_installment: float,
    initial_construction_evolution: float,
    curve_type: str,
    monthly_budget: float,
    minimum_saving_floor: float,
    annual_installment: float = 0,
    annual_installment_month: int = 12,
    evolution_start_month: int = 1
) -> pd.DataFrame:

    evolution = construction_evolution_curve(
        months=months,
        initial_value=initial_construction_evolution,
        curve_type=curve_type,
        start_month=evolution_start_month
    )

    rows = []
    accumulated_savings = 0

    for month in range(1, months + 1):
        if annual_installment > 0 and month % annual_installment_month == 0:
            annual_cost = annual_installment
        else:
            annual_cost = 0
        cost = builder_installment + evolution[month - 1] + annual_cost

        available_for_saving = monthly_budget - cost

        if available_for_saving < minimum_saving_floor:
            savings = minimum_saving_floor
            real_spending = cost + savings
            stress = max(real_spending - monthly_budget, 0)
        else:
            savings = available_for_saving
            real_spending = monthly_budget
            stress = 0

        accumulated_savings += savings

        stress_ratio = real_spending / monthly_budget if monthly_budget > 0 else np.nan

        rows.append({
            "Month": month,
            "Builder Installment": builder_installment,
            "Construction Evolution": evolution[month - 1],
            "Annual Installment": annual_cost,
            "Total Cost": cost,
            "Monthly Savings": savings,
            "Accumulated Savings": accumulated_savings,
            "Real Monthly Spending": real_spending,
            "Stress Amount": stress,
            "Stress Ratio": stress_ratio,
        })

    return pd.DataFrame(rows)