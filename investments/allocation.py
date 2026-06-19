def dynamic_allocation(
    months_remaining: int,
    monthly_contribution: float,
) -> dict:
    """
    Dynamic glide path.

    More risk early, progressively conservative near keys.
    Monthly contribution affects risk appetite:
    - low contributions reduce controlled-risk exposure
    - high contributions allow slightly higher risk early
    """

    contribution_factor = min(max(monthly_contribution / 3000, 0.6), 1.3)

    if months_remaining > 24:
        controlled_risk = 0.18 * contribution_factor
        allocation = {
            "Liquidity": 0.30,
            "PostFixed": 0.27,
            "TaxFree": 0.25,
            "ControlledRisk": controlled_risk,
        }

    elif months_remaining > 12:
        controlled_risk = 0.10 * contribution_factor
        allocation = {
            "Liquidity": 0.42,
            "PostFixed": 0.28,
            "TaxFree": 0.22,
            "ControlledRisk": controlled_risk,
        }

    else:
        controlled_risk = 0.03 * contribution_factor
        allocation = {
            "Liquidity": 0.68,
            "PostFixed": 0.18,
            "TaxFree": 0.11,
            "ControlledRisk": controlled_risk,
        }

    total = sum(allocation.values())
    return {asset: weight / total for asset, weight in allocation.items()}