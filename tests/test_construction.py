import numpy as np
import pytest

from cashflow.construction import (
    construction_evolution_curve,
    simulate_construction_phase,
)


def test_curve_aliases_support_english_and_portuguese_labels():
    for label in [
        "Linear",
        "S-Curve",
        "Back-loaded",
        "Curva em S",
        "Acumulado no final",
    ]:
        values = construction_evolution_curve(6, 1.0, label)
        assert values.shape == (6,)
        assert np.all(np.isfinite(values))


def test_simulate_construction_phase_applies_floor_and_delay():
    df = simulate_construction_phase(
        months=4,
        builder_installment=100,
        initial_construction_evolution=0,
        curve_type="Linear",
        monthly_budget=120,
        minimum_saving_floor=50,
        evolution_start_month=3,
        target_construction_evolution=200,
    )

    assert df.loc[0, "Monthly Savings"] == pytest.approx(50)
    assert df.loc[0, "Real Monthly Spending"] == pytest.approx(150)
    assert df.loc[0, "Stress Amount"] == pytest.approx(30)
    assert df.loc[0, "Construction Evolution"] == pytest.approx(0)
    assert df.loc[3, "Construction Evolution"] > 0
