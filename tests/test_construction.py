import numpy as np

from cashflow.construction import construction_evolution_curve


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
