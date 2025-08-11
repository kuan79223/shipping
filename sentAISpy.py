import socket
import time

host = '192.168.2.1'  # 接收設備的IP
port = 3333  # 接收設備的端口

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))

ais_message = "!AIVDM,1,1,,A,15M2@0047iP<000000000000,0*5A"

while True:
    sock.sendall(ais_message.encode('ascii') + b'\r\n')
    print(f"發送AIS訊號: {ais_message}")
    time.sleep(1)  # 每秒發送一次
