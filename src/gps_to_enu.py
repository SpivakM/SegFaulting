"""GPS coordinate conversion utilities."""

import logging

import numpy as np
import pandas as pd
import pymap3d

logger = logging.getLogger(__name__)

R = 6_371_000  # Mean radius of the Earth in metres


def convertGPS_to_ENU(gps_data: pd.DataFrame) -> pd.DataFrame:
    """Add ENU columns (x, y, z) to a copy of *gps_data*.

    The first row is used as the geodetic reference point (origin).

    Args:
        gps_data: DataFrame with columns Lat, Lon, Alt.

    Returns:
        A new DataFrame with additional columns x, y, z
        (East, North, Up in metres).
    """
    lat0 = gps_data["Lat"].iloc[0]
    lon0 = gps_data["Lon"].iloc[0]
    alt0 = gps_data["Alt"].iloc[0]

    e, n, u = pymap3d.geodetic2enu(
        gps_data["Lat"].to_numpy(),
        gps_data["Lon"].to_numpy(),
        gps_data["Alt"].to_numpy(),
        lat0, lon0, alt0,
    )

    result = gps_data.copy()
    result["x"] = e
    result["y"] = n
    result["z"] = u

    logger.debug("Converted %d GPS points to ENU coordinates", len(result))
    return result


def calculate_distance(gps_data: pd.DataFrame) -> float:
    """Compute the total path length using the Haversine formula.

    Args:
        gps_data: DataFrame with columns Lat and Lon (degrees).

    Returns:
        Total distance in metres.
    """
    lat = np.radians(gps_data["Lat"].to_numpy())
    lon = np.radians(gps_data["Lon"].to_numpy())

    dlat = np.diff(lat)
    dlon = np.diff(lon)

    dist = (
        2
        * R
        * np.arcsin(
            np.sqrt(
                np.clip(
                    np.sin(dlat / 2) ** 2
                    + np.cos(lat[:-1]) * np.cos(lat[1:]) * np.sin(dlon / 2) ** 2,
                    0,
                    1,
                )
            )
        )
    )
    return float(dist.sum())
