import socket
import time

# 設置發送的IP和端口（這應該是AIS接收設備的IP和端口）
host = '192.168.1.2'  # 接收設備的IP
port = 3333  # 接收設備的端口

# 創建TCP連接
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))

# 模擬的AIS訊息（這是一個簡單的範例訊息）
# 這個訊息是模擬的AIS報文，並不代表真實的船舶數據
ais_message = "!AIVDM,1,1,,A,15M2@0047iP<000000000000,0*5A"

while True:
    # 發送模擬訊號
    sock.sendall(ais_message.encode('ascii') + b'\r\n')
    print(f"發送AIS訊號: {ais_message}")

    # 設置發送間隔
    time.sleep(1)  # 每秒發送一次模擬訊息
