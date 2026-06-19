import numpy as np
import pandas as pd
from core.constants import ASSETS
from investments.allocation import dynamic_allocation


def simulate_monte_carlo(
    monthly_contributions: pd.Series,
    months_until_keys: int,
    simulations: int = 5000,
    seed: int = 42,
) -> dict:
    rng = np.random.default_rng(seed)

    final_values = []

    for _ in range(simulations):
        balances = {asset: 0.0 for asset in ASSETS.keys()}

        for idx, contribution in enumerate(monthly_contributions, start=1):
            months_remaining = months_until_keys - idx + 1
            allocation = dynamic_allocation(months_remaining, contribution)

            for asset_key, weight in allocation.items():
                asset = ASSETS[asset_key]

                mean_monthly = (1 + asset.annual_return) ** (1 / 12) - 1
                vol_monthly = asset.annual_volatility / np.sqrt(12)

                sampled_return = rng.normal(mean_monthly, vol_monthly)
                after_tax_return = sampled_return * (1 - asset.tax_rate)

                balances[asset_key] = (
                    balances[asset_key] * (1 + after_tax_return)
                    + contribution * weight
                )

        final_values.append(sum(balances.values()))

    values = np.array(final_values)

    return {
        "values": values,
        "p5": float(np.percentile(values, 5)),
        "p50": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
    }