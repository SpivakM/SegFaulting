"""IMU integration — estimates velocity from raw accelerometer/gyroscope data."""

import logging

import numpy as np
import pandas as pd
from ahrs.filters import Madgwick
from scipy.integrate import cumulative_trapezoid
from scipy.spatial.transform import Rotation

logger = logging.getLogger(__name__)


def process_imu_data(imu_data: pd.DataFrame) -> pd.DataFrame:
    """Estimate horizontal and vertical velocity from raw IMU readings.

    Uses a Madgwick AHRS filter to track orientation, rotates acceleration
    into the world frame, removes gravity, then integrates to obtain velocity.

    Args:
        imu_data: DataFrame with columns TimeUS, AccX, AccY, AccZ, GyrX, GyrY, GyrZ.

    Returns:
        A copy of *imu_data* with additional columns VelH and VelZ.
    """
    time_sec = imu_data["TimeUS"].to_numpy() / 1_000_000
    dt_mean = np.diff(time_sec).mean()
    freq = 1.0 / dt_mean if dt_mean > 0 else 100.0

    acc_data = imu_data[["AccX", "AccY", "AccZ"]].to_numpy()
    gyr_data = imu_data[["GyrX", "GyrY", "GyrZ"]].to_numpy()

    # Estimate initial roll and pitch from the first accelerometer reading.
    ax, ay, az = acc_data[0]
    i_roll = np.arctan2(ay, az)
    i_pitch = np.arctan2(-ax, np.sqrt(ay ** 2 + az ** 2))

    # Convert Euler angles to quaternion; ahrs expects (w, x, y, z) order.
    q_xyzw = Rotation.from_euler("xyz", [i_roll, i_pitch, 0.0]).as_quat()
    q0 = np.array([q_xyzw[3], q_xyzw[0], q_xyzw[1], q_xyzw[2]])

    madgwick = Madgwick(gyr_data, acc_data, frequency=freq, q0=q0)

    # Extract vector (x,y,z) and scalar (w) parts of the estimated quaternions.
    r = madgwick.Q[:, 1:]   # shape (N, 3)
    w = madgwick.Q[:, 0:1]  # shape (N, 1)

    # Rotate acceleration into the world frame via the sandwich product:
    # acc_world = acc + 2 * (r × (r × acc + w * acc))
    rv = np.cross(r, acc_data)
    rrv = np.cross(r, rv + w * acc_data)
    acc_world = acc_data + 2.0 * rrv

    # Remove the gravitational component.
    acc_world[:, 2] -= 9.81

    result = imu_data.copy()
    vel_e = cumulative_trapezoid(acc_world[:, 0], time_sec, initial=0.0)
    vel_n = cumulative_trapezoid(acc_world[:, 1], time_sec, initial=0.0)
    result["VelH"] = np.sqrt(vel_e ** 2 + vel_n ** 2)
    result["VelZ"] = -cumulative_trapezoid(acc_world[:, 2], time_sec, initial=0.0)

    logger.debug("Processed %d IMU samples at %.1f Hz", len(result), freq)
    return result
