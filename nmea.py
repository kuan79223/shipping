import socket
import pynmea2

# 設定TCP連接
host = '192.168.2.1'  # 設定為伺服器的IP
port = 3333         # 設定端口

# 建立連接
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))

while True:
    line = sock.recv(1024).decode('ascii', errors='ignore').strip()
    if line.startswith('$'):
        try:
            msg = pynmea2.parse(line)
            if line.startswith('!AIVDM'):
                # 解碼AIS訊息
                print(f"解碼AIS訊息: {msg}")
            else:
                print(f"非AIS訊息: {line}")

        except Exception as e:
            print(f"無法解析 NMEA 訊息: {line}, 錯誤原因: {e}")
