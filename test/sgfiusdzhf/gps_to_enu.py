import pymap3d
import pandas as pd
import numpy as np

R = 6_371_000 # Radius of Earth

def convertGPS_to_ENU(gps_data: pd.DataFrame) -> pd.DataFrame:
    """
    Converts Lat, Lon and Alt in GPS data to ENU
    """
    # Вибираємо стартову точку
    Lat0 = gps_data['Lat'].iloc[0]
    Lon0 = gps_data['Lon'].iloc[0]
    Alt0 = gps_data['Alt'].iloc[0]

    # Конвертуємо все в ENU
    e, n, u = pymap3d.geodetic2enu(
        gps_data['Lat'].values,
        gps_data['Lon'].values,
        gps_data['Alt'].values,
        Lat0, Lon0, Alt0
    )

    gps_data['X'] = e
    gps_data['Y'] = n
    gps_data['Z'] = u

    return gps_data

def calculate_distance(gps_data: pd.DataFrame) -> float:
    """Calculates total distance travelled by the drone with the haversine function"""
    lat = np.radians(gps_data["Lat"])
    lon = np.radians(gps_data["Lon"])

    lat_shift = lat.shift(1)
    lon_shift = lon.shift(1)

    dlat = lat - lat_shift
    dlon = lon - lon_shift

    dist = 2 * R * np.asin(np.sqrt(np.clip(np.sin(dlat / 2) ** 2 + np.cos(lat) * np.cos(lat_shift) * np.sin(dlon / 2) ** 2, 0, 1)))

    return dist.sum()

if __name__ == "__main__":
    from log_parser import get_data_from_file
    PATH = "./test_data/00000001.bin"

    gps_data, _ = get_data_from_file(PATH)
    trajectory = convertGPS_to_ENU(gps_data)

    print(trajectory[['TimeUS', 'E', 'N', 'U']])
    print(calculate_distance(gps_data))
