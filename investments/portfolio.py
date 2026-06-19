import pandas as pd
from core.constants import ASSETS
from investments.allocation import dynamic_allocation


def monthly_after_tax_return(annual_return: float, tax_rate: float) -> float:
    gross_monthly = (1 + annual_return) ** (1 / 12) - 1
    return gross_monthly * (1 - tax_rate)


def simulate_portfolio(
    contributions: pd.Series,
    months_until_keys: int,
) -> pd.DataFrame:
    balances = {asset: 0.0 for asset in ASSETS.keys()}
    rows = []

    for idx, contribution in enumerate(contributions, start=1):
        months_remaining = months_until_keys - idx + 1
        allocation = dynamic_allocation(months_remaining, contribution)

        for asset_key, weight in allocation.items():
            asset = ASSETS[asset_key]
            r = monthly_after_tax_return(asset.annual_return, asset.tax_rate)
            balances[asset_key] = balances[asset_key] * (1 + r) + contribution * weight

        total_value = sum(balances.values())
        total_contributed = contributions.iloc[:idx].sum()
        investment_gain = total_value - total_contributed

        row = {
            "Month": idx,
            "Contribution": contribution,
            "Total Portfolio": total_value,
            "Total Contributed": total_contributed,
            "Investment Gain": investment_gain,
        }

        for asset_key, value in balances.items():
            row[asset_key] = value

        rows.append(row)

    return pd.DataFrame(rows)