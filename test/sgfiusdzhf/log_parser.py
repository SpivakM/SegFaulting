from pymavlink import mavutil
import pandas as pd
from dataclasses import make_dataclass

# Dataclasses for temporary data storage
GPS_Entry = make_dataclass("GPS_Entry", [("TimeUS", int), ("Lat", float), ("Lon", float), ("Alt", float)])
IMU_Entry = make_dataclass("IMU_Entry", [("TimeUS", int), ("AccX", float), ("AccY", float), ("AccZ", float), ("GyrX", float), ("GyrY", float), ("GyrZ", float)])

def get_data_from_file(file_path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Function to parse logs

    Receives the path to a log file

    Returns a tuple of pandas Dataframes
    The first contains GPS data, for example:
           TimeUS        Lat         Lon     Alt
    0      160000 -35.363265  149.165237  584.85
    1      360000 -35.363265  149.165237  584.85
    2      560000 -35.363265  149.165237  584.85
    3      760000 -35.363265  149.165237  584.85
    4      960000 -35.363265  149.165237  584.85

    The second contains IMU data, for example:
            TimeUS       AccX       AccY       AccZ       GyrX      GyrY      GyrZ
    0            0   9.217861  -0.065573  -3.355518   0.000724  0.000728  0.000745
    1            0   9.215690  -0.065745  -3.358580   0.000590  0.000835  0.000783
    2        20000   9.216884  -0.064517  -3.356493   0.000728  0.000717  0.000768
    3        20000   9.217562  -0.062077  -3.354382   0.000582  0.000790  0.000930
    4        40000   9.217257  -0.065180  -3.356916   0.000740  0.000745  0.000737
    """
    mlog: mavutil.mavserial = mavutil.mavlink_connection(file_path)
    # Temporary data storage
    gps_list = []
    imu_list = []
    time_start = None
    while True:
        msg = mlog.recv_match(type=["GPS", "IMU"], blocking=False)

        if msg is None:
            break

        if time_start is None:
            time_start = msg.TimeUS

        msg_type = msg.get_type()
        if msg_type == "GPS":
            timeUS = msg.TimeUS - time_start
            lat = msg.Lat
            lon = msg.Lng
            alt = msg.Alt
            gps_list.append(GPS_Entry(timeUS, lat, lon, alt))
        elif msg_type == "IMU":
            # There are 2 accelerometers for redundancy. At the moment we should just focus on the readings from one of them
            if msg.I != 0: continue
            timeUS = msg.TimeUS - time_start
            accX, accY, accZ = msg.AccX, msg.AccY, msg.AccZ
            gyrX, gyrY, gyrZ = msg.GyrX, msg.GyrY, msg.GyrZ
            imu_list.append(IMU_Entry(timeUS, accX, accY, accZ, gyrX, gyrY, gyrZ))
    gps_data = pd.DataFrame(gps_list, columns=["TimeUS", "Lat", "Lon", "Alt"])
    imu_data = pd.DataFrame(imu_list, columns=["TimeUS", "AccX", "AccY", "AccZ", "GyrX", "GyrY", "GyrZ"])
    return (gps_data, imu_data)

if __name__ == "__main__":
    PATH = "C:\\Users\\Disp\\Desktop\\test_task_challenge\\00000001.bin"
    gps_data, imu_data = get_data_from_file(PATH)

    print(gps_data)
    print(imu_data)
