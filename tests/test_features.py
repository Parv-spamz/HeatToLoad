"""
Unit Tests for Feature Engineering Transformations.
"""

import numpy as np
import pandas as pd

from src.features import calculate_heat_index


def test_heat_index_values():
    # Moderate temperature, high humidity: HI should exceed temperature
    hi = calculate_heat_index(35.0, 70.0)
    assert hi is not None
    assert hi > 35.0, "High humidity at 35C should amplify perceived heat index"

    # Low temperature below Rothfusz range: simple formula
    hi_low = calculate_heat_index(22.0, 50.0)
    assert hi_low is not None
    assert 20.0 <= hi_low <= 25.0

    # Null handling
    assert calculate_heat_index(None, 50.0) is None
    assert calculate_heat_index(30.0, None) is None


def test_degree_days():
    mean_temp = pd.Series([15.0, 18.0, 25.0, 30.0])
    cdd_18 = (mean_temp - 18.0).clip(lower=0.0)
    cdd_24 = (mean_temp - 24.0).clip(lower=0.0)
    hdd_18 = (18.0 - mean_temp).clip(lower=0.0)

    assert cdd_18.tolist() == [0.0, 0.0, 7.0, 12.0]
    assert cdd_24.tolist() == [0.0, 0.0, 1.0, 6.0]
    assert hdd_18.tolist() == [3.0, 0.0, 0.0, 0.0]


def test_cyclical_encoding():
    doy = pd.Series([1, 91, 182, 273, 365])
    sin_doy = np.sin(2 * np.pi * doy / 365.25)
    cos_doy = np.cos(2 * np.pi * doy / 365.25)

    assert len(sin_doy) == 5
    # Magnitude should always be 1
    np.testing.assert_allclose(sin_doy**2 + cos_doy**2, 1.0, atol=1e-5)
