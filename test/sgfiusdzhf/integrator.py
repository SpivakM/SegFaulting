from scipy.spatial.transform import Rotation
from scipy.integrate import cumulative_trapezoid
import numpy as np
import pandas as pd
from ahrs.filters import Madgwick

def process_imu_data(imu_data: pd.DataFrame) -> pd.DataFrame:
    # Calculate frequency of the IMU
    time_sec = imu_data["TimeUS"] / 1000000
    freq = 1 / time_sec.diff().mean()

    acc_data = imu_data[["AccX", "AccY", "AccZ"]].to_numpy()
    gyr_data = imu_data[["GyrX", "GyrY", "GyrZ"]].to_numpy()

    # Initial roll and pitch of the drone. Yaw is not essential
    ax, ay, az = acc_data[0]
    i_roll = np.atan2(ay, az)
    i_pitch = np.atan2(-ax, np.sqrt(ay ** 2 + az ** 2))

    # Converting to quaternions
    q = Rotation.from_euler('xyz', [i_roll, i_pitch, 0]).as_quat()
    q0 = np.array((q[3], q[0], q[1], q[2]))
    
    # Applying Magdwick filter to the data to get orientation data
    magdwick = Madgwick(gyr_data, acc_data, frequency=freq, q0=q0) #wxyz
    
    # Quaternion values
    r = magdwick.Q[:, 1:]
    w = magdwick.Q[:, 0:1]

    # Rotating acceleration vectors by the quaternion values
    rv = np.cross(r, acc_data)
    rrv = np.cross(r, rv + w * acc_data)
    acc_world = acc_data + 2 * rrv    
    # Subtracting g
    acc_world[:, 2] -= 9.81
    
    # Output
    vel_data = pd.DataFrame()
    vel_data["VelH"] = np.sqrt(cumulative_trapezoid(y=acc_world[:, 0], x=time_sec, initial=0) ** 2 + cumulative_trapezoid(y=acc_world[:, 1], x=time_sec, initial=0) ** 2)
    vel_data["VelZ"] = -cumulative_trapezoid(y=acc_world[:, 2], x=time_sec, initial=0)
    return vel_data


if __name__ == "__main__":
    PATH = "C:\\Users\\Disp\\Desktop\\test_task_challenge\\00000001.bin"
    from log_parser import get_data_from_file
    from timeit import timeit
    _, imu_data = get_data_from_file(PATH)
    print(imu_data)

    data = process_imu_data(imu_data)

    print(data)
    import matplotlib.pyplot as plt

    plt.plot(imu_data["TimeUS"] / 1000000, data["VelH"])
    plt.plot(imu_data["TimeUS"] / 1000000, data["VelZ"])
    plt.show()

    # N = 100
    # print(timeit("process_imu_data(imu_data)", setup="from __main__ import imu_data, process_imu_data", number=N) / N)