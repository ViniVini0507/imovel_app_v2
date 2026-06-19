import pandas as pd
import numpy as np


def annual_to_monthly_rate(annual_rate: float) -> float:
    return (1 + annual_rate) ** (1 / 12) - 1


def generate_sac_schedule(
    principal: float,
    annual_rate: float,
    term_months: int,
) -> pd.DataFrame:
    monthly_rate = annual_to_monthly_rate(annual_rate)
    amortization = principal / term_months
    balance = principal

    rows = []

    for month in range(1, term_months + 1):
        interest = balance * monthly_rate
        payment = amortization + interest
        ending_balance = max(balance - amortization, 0)

        rows.append({
            "Month": month,
            "Opening Balance": balance,
            "Interest": interest,
            "Amortization": amortization,
            "Payment": payment,
            "Ending Balance": ending_balance,
        })

        balance = ending_balance

    return pd.DataFrame(rows)


def generate_price_schedule(
    principal: float,
    annual_rate: float,
    term_months: int,
) -> pd.DataFrame:
    monthly_rate = annual_to_monthly_rate(annual_rate)

    if monthly_rate == 0:
        payment = principal / term_months
    else:
        payment = principal * (
            monthly_rate * (1 + monthly_rate) ** term_months
        ) / ((1 + monthly_rate) ** term_months - 1)

    balance = principal
    rows = []

    for month in range(1, term_months + 1):
        interest = balance * monthly_rate
        amortization = payment - interest
        ending_balance = max(balance - amortization, 0)

        rows.append({
            "Month": month,
            "Opening Balance": balance,
            "Interest": interest,
            "Amortization": amortization,
            "Payment": payment,
            "Ending Balance": ending_balance,
        })

        balance = ending_balance

    return pd.DataFrame(rows)


def generate_amortization_schedule(
    system: str,
    principal: float,
    annual_rate: float,
    term_months: int,
) -> pd.DataFrame:
    if system == "SAC":
        return generate_sac_schedule(principal, annual_rate, term_months)

    if system == "PRICE":
        return generate_price_schedule(principal, annual_rate, term_months)

    raise ValueError(f"Unsupported financing system: {system}")


def simulate_extra_amortization(
    schedule: pd.DataFrame,
    extra_payment: float,
    month: int = 1,
) -> dict:
    if extra_payment <= 0:
        return {
            "new_schedule": schedule.copy(),
            "interest_saved": 0,
            "months_reduced": 0,
        }

    original_total_interest = schedule["Interest"].sum()

    principal = max(schedule.loc[schedule["Month"] == month, "Opening Balance"].iloc[0] - extra_payment, 0)
    annualized_monthly_rate = schedule.loc[0, "Interest"] / schedule.loc[0, "Opening Balance"]

    remaining_months = int(schedule["Month"].max() - month + 1)

    monthly_rate = annualized_monthly_rate
    amortization = principal / remaining_months

    rows = []
    balance = principal

    for m in range(month, month + remaining_months):
        interest = balance * monthly_rate
        payment = amortization + interest
        ending_balance = max(balance - amortization, 0)

        rows.append({
            "Month": m,
            "Opening Balance": balance,
            "Interest": interest,
            "Amortization": amortization,
            "Payment": payment,
            "Ending Balance": ending_balance,
        })

        balance = ending_balance

    new_schedule = pd.DataFrame(rows)
    new_total_interest = schedule[schedule["Month"] < month]["Interest"].sum() + new_schedule["Interest"].sum()

    return {
        "new_schedule": new_schedule,
        "interest_saved": original_total_interest - new_total_interest,
        "months_reduced": 0,
    }