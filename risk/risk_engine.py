import numpy as np


def score_income_commitment(first_installment: float, household_income: float) -> dict:
    ratio = first_installment / household_income if household_income > 0 else 1

    if ratio <= 0.25:
        score = 100
        status = "green"
    elif ratio <= 0.35:
        score = 75
        status = "yellow"
    elif ratio <= 0.45:
        score = 45
        status = "yellow"
    else:
        score = 20
        status = "red"

    return {
        "ratio": ratio,
        "score": score,
        "status": status,
    }


def score_savings_stress(avg_stress_ratio: float, max_stress_ratio: float) -> dict:
    penalty = 0

    penalty += max((avg_stress_ratio - 1) * 100, 0)
    penalty += max((max_stress_ratio - 1) * 150, 0)

    score = max(100 - penalty, 0)

    if score >= 75:
        status = "green"
    elif score >= 50:
        status = "yellow"
    else:
        status = "red"

    return {
        "score": score,
        "status": status,
    }


def score_renovation_coverage(projected_cash: float, renovation_cost: float) -> dict:
    coverage = projected_cash / renovation_cost if renovation_cost > 0 else 1

    if coverage >= 1.2:
        score = 100
        status = "green"
    elif coverage >= 0.85:
        score = 70
        status = "yellow"
    elif coverage >= 0.6:
        score = 45
        status = "yellow"
    else:
        score = 20
        status = "red"

    return {
        "coverage": coverage,
        "score": score,
        "status": status,
    }


def compute_overall_risk_score(
    income_commitment: dict,
    savings_stress: dict,
    renovation_coverage: dict,
) -> dict:
    weighted_score = (
        income_commitment["score"] * 0.40
        + savings_stress["score"] * 0.30
        + renovation_coverage["score"] * 0.30
    )

    if weighted_score >= 75:
        status = "green"
    elif weighted_score >= 50:
        status = "yellow"
    else:
        status = "red"

    return {
        "score": round(weighted_score, 1),
        "status": status,
    }


def full_risk_assessment(
    first_installment: float,
    household_income: float,
    avg_stress_ratio: float,
    max_stress_ratio: float,
    projected_cash: float,
    renovation_cost: float,
) -> dict:
    income = score_income_commitment(first_installment, household_income)
    savings = score_savings_stress(avg_stress_ratio, max_stress_ratio)
    renovation = score_renovation_coverage(projected_cash, renovation_cost)

    overall = compute_overall_risk_score(income, savings, renovation)

    return {
        "income_commitment": income,
        "savings_stress": savings,
        "renovation_coverage": renovation,
        "overall": overall,
    }