"""Unit tests for the gps_to_enu module."""

import numpy as np
import pandas as pd
import pytest

from gps_to_enu import calculate_distance, convertGPS_to_ENU


def _make_gps(lats, lons, alts=None, times=None):
    n = len(lats)
    if alts is None:
        alts = [0.0] * n
    if times is None:
        times = list(range(n))
    return pd.DataFrame({"TimeUS": times, "Lat": lats, "Lon": lons, "Alt": alts})


class TestConvertGPSToENU:
    def test_origin_is_zero(self):
        df = _make_gps([-35.0, -35.001, -35.002], [149.0, 149.001, 149.002])
        result = convertGPS_to_ENU(df)
        assert result["x"].iloc[0] == pytest.approx(0.0, abs=1e-6)
        assert result["y"].iloc[0] == pytest.approx(0.0, abs=1e-6)
        assert result["z"].iloc[0] == pytest.approx(0.0, abs=1e-6)

    def test_adds_xyz_columns(self):
        df = _make_gps([-35.0, -35.001], [149.0, 149.001])
        result = convertGPS_to_ENU(df)
        assert "x" in result.columns
        assert "y" in result.columns
        assert "z" in result.columns

    def test_does_not_mutate_input(self):
        df = _make_gps([-35.0, -35.001], [149.0, 149.001])
        original_cols = set(df.columns)
        convertGPS_to_ENU(df)
        assert set(df.columns) == original_cols

    def test_east_positive_for_east_movement(self):
        # Moving east → positive x
        df = _make_gps([-35.0, -35.0], [149.0, 149.01])
        result = convertGPS_to_ENU(df)
        assert result["x"].iloc[1] > 0

    def test_north_positive_for_north_movement(self):
        # Moving north → positive y
        df = _make_gps([-35.0, -34.9], [149.0, 149.0])
        result = convertGPS_to_ENU(df)
        assert result["y"].iloc[1] > 0

    def test_altitude_delta_reflected_in_z(self):
        df = _make_gps([-35.0, -35.0], [149.0, 149.0], alts=[100.0, 200.0])
        result = convertGPS_to_ENU(df)
        assert result["z"].iloc[1] == pytest.approx(100.0, rel=1e-3)


class TestCalculateDistance:
    def test_stationary_is_zero(self):
        df = _make_gps([-35.0, -35.0, -35.0], [149.0, 149.0, 149.0])
        assert calculate_distance(df) == pytest.approx(0.0, abs=1e-6)

    def test_one_degree_latitude_is_approx_111km(self):
        df = _make_gps([-35.0, -36.0], [149.0, 149.0])
        dist = calculate_distance(df)
        assert 110_000 < dist < 112_000

    def test_returns_float(self):
        df = _make_gps([-35.0, -35.001], [149.0, 149.001])
        assert isinstance(calculate_distance(df), float)

    def test_distance_is_non_negative(self):
        df = _make_gps([-35.0, -35.005, -35.01], [149.0, 149.005, 149.01])
        assert calculate_distance(df) >= 0

    def test_two_point_trip_equals_return_trip(self):
        df_out = _make_gps([-35.0, -35.01], [149.0, 149.01])
        df_back = _make_gps([-35.01, -35.0], [149.01, 149.0])
        assert calculate_distance(df_out) == pytest.approx(calculate_distance(df_back), rel=1e-9)
