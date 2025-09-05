import serial
import time

# 替換為你的串口號和波特率
SERIAL_PORT = 'COM3'  # Windows系統
# SERIAL_PORT = '/dev/ttyUSB0'  # Linux系統
BAUD_RATE = 38400  # 一般AIS設備的常見波特率

# 開啟串口
# ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

# parity='N' (無奇偶校驗)  stopbits=1 (1位停止位) bytesize=8 (8位數據位)
# 避免亂碼
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1, parity='N', stopbits=1, bytesize=8)

try:
    with open("ais_log1.txt", "a", encoding="utf-8") as txt_file_write:
        while True:
            if ser.in_waiting > 0:
                # 讀取AIS數據
                data = ser.readline()

                if data:
                    decode_ais = data.decode('ascii', errors='ignore')
                    print(decode_ais)
                    txt_file_write.writelines(decode_ais)
                    txt_file_write.flush()

            time.sleep(0.1)

except KeyboardInterrupt:
    print("程序中斷")
finally:
    ser.close()
