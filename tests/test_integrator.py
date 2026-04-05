"""Unit tests for the integrator module."""

import numpy as np
import pandas as pd
import pytest

from integrator import process_imu_data


def _make_imu(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic IMU data mimicking a hovering drone at ~100 Hz."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) * 10_000  # 10 ms steps → 100 Hz
    # Predominantly upward acceleration (hovering), small noise
    acc = np.tile([0.0, 0.0, 9.81], (n, 1)) + rng.normal(0, 0.01, (n, 3))
    gyr = rng.normal(0, 0.001, (n, 3))
    return pd.DataFrame({
        "TimeUS": t.astype(np.int64),
        "AccX": acc[:, 0], "AccY": acc[:, 1], "AccZ": acc[:, 2],
        "GyrX": gyr[:, 0], "GyrY": gyr[:, 1], "GyrZ": gyr[:, 2],
    })


def test_adds_velocity_columns():
    df = _make_imu()
    result = process_imu_data(df)
    assert "VelH" in result.columns
    assert "VelZ" in result.columns


def test_output_length_matches_input():
    df = _make_imu(150)
    result = process_imu_data(df)
    assert len(result) == 150


def test_does_not_mutate_input():
    df = _make_imu()
    original_cols = set(df.columns)
    original_data = df.copy()
    process_imu_data(df)
    assert set(df.columns) == original_cols
    pd.testing.assert_frame_equal(df, original_data)


def test_velh_is_non_negative():
    """VelH = sqrt(velE² + velN²) must always be ≥ 0."""
    df = _make_imu()
    result = process_imu_data(df)
    assert (result["VelH"] >= 0).all()


def test_initial_velocity_is_zero():
    """Integration with initial=0 means VelH[0] == 0."""
    df = _make_imu()
    result = process_imu_data(df)
    assert result["VelH"].iloc[0] == pytest.approx(0.0, abs=1e-9)
    assert result["VelZ"].iloc[0] == pytest.approx(0.0, abs=1e-9)


def test_output_values_are_finite():
    df = _make_imu()
    result = process_imu_data(df)
    assert np.isfinite(result["VelH"].to_numpy()).all()
    assert np.isfinite(result["VelZ"].to_numpy()).all()
