import numpy as np
import pandas as pd


_CURVE_ALIASES = {
    "Linear": "Linear",
    "linear": "Linear",
    "Curva linear": "Linear",
    "curva linear": "Linear",
    "S-Curve": "S-Curve",
    "s-curve": "S-Curve",
    "S Curve": "S-Curve",
    "s curve": "S-Curve",
    "Curva em S": "S-Curve",
    "curva em s": "S-Curve",
    "Back-loaded": "Back-loaded",
    "back-loaded": "Back-loaded",
    "Back loaded": "Back-loaded",
    "back loaded": "Back-loaded",
    "Acumulado no final": "Back-loaded",
    "acumulado no final": "Back-loaded",
}


def _normalize_curve_type(curve_type: str) -> str:
    normalized = str(curve_type).strip()
    return _CURVE_ALIASES.get(normalized, normalized)


def construction_evolution_curve(
    months: int,
    initial_value: float,
    curve_type: str,
    target_value: float | None = None,
    start_month: int = 1,
    sigmoid_steepness: float = 1.6,
    backloaded_exponent: float = 2.5,
) -> np.ndarray:
    """
    Gera a curva de evolução da obra com início atrasado.

    Linear: interpolação reta entre valor inicial e alvo.
    S-Curve: crescimento lento -> acelerado -> estabiliza (sigmoide).
    Back-loaded: custo concentrado perto da entrega (curva convexa).
    """
    try:
        months = int(months)
        start_month = int(start_month)
        initial_value = float(initial_value)
        target_value = float(target_value) if target_value is not None else initial_value
    except (TypeError, ValueError):
        return np.zeros(0, dtype=float)

    curve_type = _normalize_curve_type(curve_type)
    evolution = np.zeros(months, dtype=float)

    if months <= 0:
        return evolution

    if start_month <= 1:
        active_months = months
    else:
        active_months = max(months - start_month + 1, 0)

    if active_months <= 0:
        return evolution

    if active_months == 1:
        evolution[start_month - 1:] = target_value
        return evolution

    delta = target_value - initial_value

    if curve_type == "Linear":
        values = np.linspace(initial_value, target_value, active_months)

    elif curve_type == "S-Curve":
        t = np.linspace(-6, 6, active_months) * sigmoid_steepness / 3.0
        sigmoid = 1 / (1 + np.exp(-t))
        sigmoid_norm = (sigmoid - sigmoid.min()) / (sigmoid.max() - sigmoid.min())
        values = initial_value + delta * sigmoid_norm

    elif curve_type == "Back-loaded":
        fraction = np.linspace(0.0, 1.0, active_months)
        convex = fraction ** backloaded_exponent
        values = initial_value + delta * convex

    else:
        raise ValueError(f"Unknown curve type: {curve_type}")

    evolution[start_month - 1:] = values
    return evolution


def simulate_construction_phase(
    months: int,
    builder_installment: float,
    initial_construction_evolution: float,
    curve_type: str,
    monthly_budget: float,
    minimum_saving_floor: float,
    annual_installment: float = 0,
    annual_installment_month: int = 12,
    evolution_start_month: int = 1,
    target_construction_evolution: float | None = None,
) -> pd.DataFrame:
    try:
        builder_installment = float(builder_installment)
        initial_construction_evolution = float(initial_construction_evolution)
        monthly_budget = float(monthly_budget)
        minimum_saving_floor = float(minimum_saving_floor)
        annual_installment = float(annual_installment)
        evolution_start_month = int(evolution_start_month)
        target_construction_evolution = (
            float(target_construction_evolution)
            if target_construction_evolution is not None
            else initial_construction_evolution
        )
    except (TypeError, ValueError):
        builder_installment = 0.0
        initial_construction_evolution = 0.0
        monthly_budget = 0.0
        minimum_saving_floor = 0.0
        annual_installment = 0.0
        evolution_start_month = 1
        target_construction_evolution = 0.0

    evolution = construction_evolution_curve(
        months=months,
        initial_value=initial_construction_evolution,
        curve_type=curve_type,
        target_value=target_construction_evolution,
        start_month=evolution_start_month,
    )

    rows = []
    accumulated_savings = 0.0

    for month in range(1, months + 1):
        if annual_installment > 0 and month % annual_installment_month == 0:
            annual_cost = annual_installment
        else:
            annual_cost = 0.0

        monthly_evolution = float(evolution[month - 1])
        total_cost = builder_installment + monthly_evolution + annual_cost
        projected_savings = monthly_budget - total_cost

        if projected_savings < minimum_saving_floor:
            savings = minimum_saving_floor
            real_spending = total_cost + minimum_saving_floor
            stress = max(real_spending - monthly_budget, 0)
        else:
            savings = projected_savings
            real_spending = monthly_budget
            stress = 0.0

        accumulated_savings += savings
        stress_ratio = real_spending / monthly_budget if monthly_budget > 0 else np.nan

        rows.append({
            "Month": month,
            "Builder Installment": builder_installment,
            "Construction Evolution": monthly_evolution,
            "Annual Installment": annual_cost,
            "Total Cost": total_cost,
            "Monthly Savings": savings,
            "Accumulated Savings": accumulated_savings,
            "Real Monthly Spending": real_spending,
            "Stress Amount": stress,
            "Stress Ratio": stress_ratio,
        })

    return pd.DataFrame(rows)
