import pandas as pd
from core.constants import RENOVATION_PACKAGES


def estimate_renovation_cost(
    apartment_size_m2: float,
    package: str,
    months_until_keys: int,
    annual_inflation: float,
) -> pd.DataFrame:

    if package not in RENOVATION_PACKAGES:
        raise ValueError(f"Invalid renovation package: {package}")

    inflation_factor = (1 + annual_inflation) ** (months_until_keys / 12)
    package_costs = RENOVATION_PACKAGES[package]

    rows = []

    for category, cost_per_m2 in package_costs.items():
        base_cost = apartment_size_m2 * cost_per_m2
        inflated_cost = base_cost * inflation_factor

        rows.append({
            "Category": category.replace("_", " ").title(),
            "Base Cost": base_cost,
            "Inflated Cost": inflated_cost,
            "Cost per m²": cost_per_m2,
        })

    df = pd.DataFrame(rows)
    df["Share"] = df["Inflated Cost"] / df["Inflated Cost"].sum()

    return df