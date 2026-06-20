import pandas as pd
from core.constants import RENOVATION_PACKAGES


# Custo realista por unidade de ar-condicionado, variando por pacote.
AC_UNIT_COST_BY_PACKAGE = {
    "Basic": 2200,        # split 9.000 BTU genérico
    "Recommended": 3500,  # split inverter padrão
    "Premium": 5000,      # split inverter alta eficiência
}


def estimate_renovation_cost(
    apartment_size_m2: float,
    package: str,
    months_until_keys: int,
    annual_inflation: float,
    num_ares: int = 3,
) -> pd.DataFrame:
    package_aliases = {
        "Basic": "Basic",
        "basic": "Basic",
        "Básico": "Basic",
        "basico": "Basic",
        "Recommended": "Recommended",
        "recommended": "Recommended",
        "Recomendado": "Recommended",
        "recomendado": "Recommended",
        "Premium": "Premium",
        "premium": "Premium",
    }
    resolved_package = package_aliases.get(str(package).strip(), str(package).strip())

    if resolved_package not in RENOVATION_PACKAGES:
        raise ValueError(f"Invalid renovation package: {package}")

    inflation_factor = (1 + annual_inflation) ** (months_until_keys / 12)
    package_costs = RENOVATION_PACKAGES[resolved_package]

    rows = []

    for category, cost_per_m2 in package_costs.items():
        if category == "ac":
            custo_unitario = AC_UNIT_COST_BY_PACKAGE.get(resolved_package, 6000)
            base_cost = num_ares * custo_unitario
        else:
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
