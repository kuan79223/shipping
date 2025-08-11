import json
import socket
import pyais  # 這是為了解析 AIS 訊息
import time
import json

host = '192.168.2.1'  # 設定為伺服器的IP
port = 3333            # 設定端口

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))

start_time = time.time()
with open('ais_data.json', 'w') as json_file:
    while True:
        line = sock.recv(1024).decode('ascii', errors='ignore').strip()

        if line.startswith('!AIVDM'):
            print(f'接收訊號時間: {round(time.time() - start_time)}')
            try:
                ais_msg = pyais.decode(line.encode('utf-8'))
                print(f"AIS 訊息: {ais_msg.}")
                # dict_ais_msg = ais_msg.__dict__
                # print(dict_ais_msg)
                # json.dump(dict_ais_msg, json_file, indent=4)
                # json_file.write('\n')

            except Exception as e:
                print(f'接收的訊息: {line}')

    # else:
        # print(f"非 AIS 或 NMEA 訊息: {line}")
