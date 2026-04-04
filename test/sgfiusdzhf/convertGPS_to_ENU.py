import pymap3d
import pandas

from log_parser import get_data_from_file

def convertGPS_to_ENU(file_path):
    gps_data, imu_data = get_data_from_file(file_path)

    #вибираємо стартову точку
    Lat0 = gps_data['Lat'].iloc[0]
    Lon0 = gps_data['Lon'].iloc[0]
    Alt0 = gps_data['Alt'].iloc[0]

    #конвертуємо все в ENU
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


if __name__ == "__main__":
    PATH = "/Users/bogdanstrutinskij/documents/NULP/HAKATHON/test_task_challenge/00000001.bin"

    trajectory = convertGPS_to_ENU(PATH)

    print(trajectory[['TimeUS', 'X_East_m', 'Y_North_m', 'Z_Up_m']])
