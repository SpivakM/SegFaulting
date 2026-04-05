"""MAVLink log file parser — returns GPS and IMU DataFrames."""

import logging

import pandas as pd
from pymavlink import mavutil

logger = logging.getLogger(__name__)


def get_data_from_file(file_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse an ArduPilot binary log and return GPS and IMU data.

    Args:
        file_path: Path to a MAVLink binary log (.bin / .log).

    Returns:
        A 2-tuple (gps_data, imu_data):
        - gps_data has columns: TimeUS, Lat, Lon, Alt
        - imu_data has columns: TimeUS, AccX, AccY, AccZ, GyrX, GyrY, GyrZ
    """
    logger.info("Opening log file: %s", file_path)
    mlog: mavutil.mavserial = mavutil.mavlink_connection(file_path)

    gps_list: list[dict] = []
    imu_list: list[dict] = []
    time_start: int | None = None

    while True:
        msg = mlog.recv_match(type=["GPS", "IMU"], blocking=False)
        if msg is None:
            break

        if time_start is None:
            time_start = msg.TimeUS

        msg_type = msg.get_type()
        if msg_type == "IMU":
            # Use only the primary accelerometer (I == 0) to avoid duplicate readings.
            if msg.I != 0:
                continue
            time_us = msg.TimeUS - time_start
            imu_list.append({
                "TimeUS": time_us,
                "AccX": msg.AccX, "AccY": msg.AccY, "AccZ": msg.AccZ,
                "GyrX": msg.GyrX, "GyrY": msg.GyrY, "GyrZ": msg.GyrZ,
            })
        elif msg_type == "GPS":
            # Only include GPS fixes (Status >= 3 means 3D fix).
            if getattr(msg, "Status", 0) < 3:
                continue
            time_us = msg.TimeUS - time_start
            gps_list.append({
                "TimeUS": time_us,
                "Lat": msg.Lat, "Lon": msg.Lng, "Alt": msg.Alt,
            })

    gps_data = pd.DataFrame(gps_list, columns=["TimeUS", "Lat", "Lon", "Alt"])
    imu_data = pd.DataFrame(
        imu_list,
        columns=["TimeUS", "AccX", "AccY", "AccZ", "GyrX", "GyrY", "GyrZ"],
    )

    logger.info(
        "Parsed %d GPS rows and %d IMU rows from %s",
        len(gps_data),
        len(imu_data),
        file_path,
    )
    return gps_data, imu_data
