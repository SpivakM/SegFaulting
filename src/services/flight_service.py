"""Flight data processing service."""

import logging
import os

import numpy as np
import pandas as pd

from gps_to_enu import calculate_distance, convertGPS_to_ENU
from integrator import process_imu_data
from log_parser import get_data_from_file

logger = logging.getLogger(__name__)


def process_flight_data(
    file_path: str,
    data_dir: str,
    session_id: str,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Parse log file, convert GPS to ENU, integrate IMU, and write merged CSV.

    Args:
        file_path: Path to the uploaded ArduPilot binary log file.
        data_dir: Directory where the processed CSV should be written.
        session_id: Unique session identifier used to name the output file.

    Returns:
        A 3-tuple (gps_data, imu_data, data_path):
        - gps_data: DataFrame with columns x, y, z, timestamp, VelH
        - imu_data: DataFrame with IMU columns plus VelH and VelZ
        - data_path: Absolute path of the written CSV file

    Raises:
        ValueError: if the log file yields no valid GPS or IMU data.
    """
    logger.info("Parsing log file: %s", file_path)
    gps_data, imu_data = get_data_from_file(file_path)

    if gps_data.empty:
        raise ValueError("No valid GPS data found in the log file.")
    if imu_data.empty:
        raise ValueError("No valid IMU data found in the log file.")
    if len(gps_data) < 2:
        raise ValueError("Not enough GPS data points for analysis (need at least 2).")
    if len(imu_data) < 2:
        raise ValueError("Not enough IMU data points for analysis (need at least 2).")

    gps_data = convertGPS_to_ENU(gps_data)
    imu_data = process_imu_data(imu_data)

    gps_data = pd.merge_asof(
        gps_data,
        imu_data[["TimeUS", "VelH"]],
        on="TimeUS",
        direction="nearest",
    )
    gps_data = gps_data.rename(columns={"TimeUS": "timestamp"})

    data_path = os.path.join(data_dir, f"{session_id}_data.csv")
    gps_data[["x", "y", "z", "timestamp", "VelH"]].to_csv(data_path, index=False)
    logger.info("Wrote flight CSV to %s", data_path)

    return gps_data, imu_data, data_path


def compute_stats(gps_data: pd.DataFrame, imu_data: pd.DataFrame) -> dict:
    """Compute flight statistics from processed GPS and IMU DataFrames.

    Args:
        gps_data: DataFrame containing ENU coordinates and a 'timestamp' column.
        imu_data: DataFrame containing IMU readings plus VelH and VelZ columns.

    Returns:
        A dict of scalar flight metrics (distances in metres, velocities in m/s,
        accelerations in m/s², time in seconds).

    Raises:
        ValueError: if either DataFrame is empty.
    """
    if gps_data.empty or imu_data.empty:
        raise ValueError("Cannot compute stats from empty DataFrames.")

    stats: dict = {}
    stats["total_distance"] = calculate_distance(gps_data)
    stats["max_velocity_h"] = float(imu_data["VelH"].max())
    stats["max_velocity_v"] = float(imu_data["VelZ"].max())
    stats["max_velocity"] = float(np.hypot(imu_data["VelH"], imu_data["VelZ"]).max())

    time_start = float(imu_data.iloc[0]["TimeUS"])
    time_end = float(imu_data.iloc[-1]["TimeUS"])
    total_time = (time_end - time_start) / 1_000_000  # µs → s
    stats["total_time"] = total_time

    imu_copy = imu_data.copy()
    imu_copy["AccH"] = np.hypot(imu_copy["AccX"], imu_copy["AccY"])
    stats["max_acc_h"] = float(imu_copy["AccH"].max())
    stats["max_acc_v"] = float(imu_copy["AccZ"].max())
    stats["max_acc"] = float(np.hypot(imu_copy["AccH"], imu_copy["AccZ"]).max())

    stats["average_velocity"] = stats["total_distance"] / total_time if total_time > 0 else 0.0
    stats["max_altitude"] = float(gps_data["z"].max())
    stats["min_altitude"] = float(gps_data["z"].min())
    stats["altitude_amp"] = stats["max_altitude"] - stats["min_altitude"]

    first = gps_data.iloc[0]
    last = gps_data.iloc[-1]
    stats["displacement_h"] = float(np.hypot(last["x"] - first["x"], last["y"] - first["y"]))

    return stats
