"""Unit tests for the log_parser module."""

import os

import pandas as pd
import pytest

from log_parser import get_data_from_file

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")
BIN_FILES = [f for f in os.listdir(TEST_DATA_DIR) if f.lower().endswith(".bin")]


@pytest.mark.parametrize("filename", BIN_FILES)
def test_returns_tuple_of_dataframes(filename):
    path = os.path.join(TEST_DATA_DIR, filename)
    result = get_data_from_file(path)
    assert isinstance(result, tuple)
    assert len(result) == 2
    gps, imu = result
    assert isinstance(gps, pd.DataFrame)
    assert isinstance(imu, pd.DataFrame)


@pytest.mark.parametrize("filename", BIN_FILES)
def test_gps_has_required_columns(filename):
    path = os.path.join(TEST_DATA_DIR, filename)
    gps, _ = get_data_from_file(path)
    for col in ("TimeUS", "Lat", "Lon", "Alt"):
        assert col in gps.columns, f"Missing column '{col}' in GPS data"


@pytest.mark.parametrize("filename", BIN_FILES)
def test_imu_has_required_columns(filename):
    path = os.path.join(TEST_DATA_DIR, filename)
    _, imu = get_data_from_file(path)
    for col in ("TimeUS", "AccX", "AccY", "AccZ", "GyrX", "GyrY", "GyrZ"):
        assert col in imu.columns, f"Missing column '{col}' in IMU data"


@pytest.mark.parametrize("filename", BIN_FILES)
def test_data_is_non_empty(filename):
    path = os.path.join(TEST_DATA_DIR, filename)
    gps, imu = get_data_from_file(path)
    assert len(gps) > 0, "GPS DataFrame should not be empty"
    assert len(imu) > 0, "IMU DataFrame should not be empty"


@pytest.mark.parametrize("filename", BIN_FILES)
def test_gps_timestamps_are_non_negative(filename):
    path = os.path.join(TEST_DATA_DIR, filename)
    gps, _ = get_data_from_file(path)
    assert (gps["TimeUS"] >= 0).all()


@pytest.mark.parametrize("filename", BIN_FILES)
def test_imu_timestamps_are_non_negative(filename):
    path = os.path.join(TEST_DATA_DIR, filename)
    _, imu = get_data_from_file(path)
    assert (imu["TimeUS"] >= 0).all()
