import json
import socket
import pyais  # 這是為了解析 AIS 訊息
import json

host = '192.168.2.1'  # 設定為伺服器的IP
port = 3333            # 設定端口

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))

with open('ais_data.json', 'w') as json_file:
    while True:
        line = sock.recv(1024).decode('ascii', errors='ignore').strip()
        if line.startswith('!AIVDM'):
            try:
                # 將收到的訊號解碼
                ais_msg = pyais.decode(line.encode('utf-8'))
                print(f'解碼訊號: {ais_msg}')
                # 原因分析：
                # pyais.decode() 解碼返回的對象是某種類型的 MessageType 物件，
                # 而這些物件並不一定會直接將所有屬性展開為字典屬性。當你調用 ais_msg.__dict__ 時，它只會返回該物件的屬性字典，
                # 如果這些屬性是通過其他方式（如方法或特殊屬性）存儲的，則不會顯示在 __dict__ 中。
                dict_ais_msg = {
                    'msg_type': ais_msg.msg_type,
                    'repeat': ais_msg.repeat,
                    'mmsi': ais_msg.mmsi,
                    'status': ais_msg.status.name,  # Enum類型轉為字串
                    'turn': ais_msg.turn,
                    'speed': ais_msg.speed,
                    'accuracy': ais_msg.accuracy,
                    'lon': ais_msg.lon,
                    'lat': ais_msg.lat,
                    'course': ais_msg.course,
                    'heading': ais_msg.heading,
                    'second': ais_msg.second,
                    'maneuver': ais_msg.maneuver.name,  # Enum類型轉為字串
                    'spare_1': ais_msg.spare_1,
                    'raim': ais_msg.raim,
                    'radio': ais_msg.radio
                }
                json.dump(dict_ais_msg, json_file, indent=4)
                json_file.write('\n')

            except Exception as e:
                print(f'接收的訊息: {line}')

    # else:
        # print(f"非 AIS 或 NMEA 訊息: {line}")
