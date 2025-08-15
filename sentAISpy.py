import socket
import time

host = '192.168.2.1'  # 接收設備的IP
port = 3333  # 接收設備的端口

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))

# 一則 AIS 訊息拆成兩段
ais_msg_part1 = "!AIVDM,2,1,6,A,53HOvt4000000@E>220T4pF22222222222222216<5qJ0Ht0E=@E53`888,0*6D"
ais_msg_part2 = "!AIVDM,2,2,6,A,88888888880,2*25"


while True:
    sock.sendall(ais_msg_part1.encode('ascii') + b'\r\n')
    time.sleep(0.5)
    # 再發第二行
    sock.sendall(ais_msg_part2.encode('ascii') + b'\r\n')
    print("發送一則 AIS 訊號（兩行）完成")
    time.sleep(2)  # 間隔再發送
