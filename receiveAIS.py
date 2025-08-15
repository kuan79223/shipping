import json
import socket
import pyais  # 這是為了解析 AIS 訊息
from datetime import datetime, timedelta

host = '192.168.2.1'  # 設定為伺服器的IP
port = 3333  # 設定端口

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))

# 紀錄訊號數量
signal_count = 0
start_time = datetime.now()  # 程式開始時間

LOG_PATH = "ais_data_24V.ndjson"  # 設定 NDJSON 檔案儲存 AIS 訊息

try:
    with open(LOG_PATH, 'a', encoding='utf-8') as json_file:
        print(f'{start_time} Start...')
        while True:
            # 記錄本次接收的時間戳（台北時間）
            now_time = datetime.now()

            line = sock.recv(1024).decode('ascii', errors='ignore').strip()
            if line.startswith('!AIVDM'):
                # 每接收一條訊息，就更新訊號數量
                signal_count += 1
                try:
                    # 將收到的訊號解碼
                    ais_msg = pyais.decode(line.encode('utf-8'))
                    print(f'解碼訊號: {ais_msg}')

                    # 將訊息轉換為字典格式
                    # dict_ais_msg = {
                    #     'msg_type': ais_msg.msg_type,
                    #     'repeat': ais_msg.repeat,
                    #     'mmsi': ais_msg.mmsi,
                    #     'status': ais_msg.status.name,  # Enum類型轉為字串
                    #     'turn': ais_msg.turn,
                    #     'speed': ais_msg.speed,
                    #     'accuracy': ais_msg.accuracy,
                    #     'lon': ais_msg.lon,
                    #     'lat': ais_msg.lat,
                    #     'course': ais_msg.course,
                    #     'heading': ais_msg.heading,
                    #     'second': ais_msg.second,
                    #     'maneuver': ais_msg.maneuver.name,  # Enum類型轉為字串
                    #     'spare_1': getattr(ais_msg.spare_1, 'spare_1', None),
                    #     'raim': ais_msg.raim,
                    #     'radio': ais_msg.radio,
                    #     'recv_ts': now_time.isoformat()  # 記錄接收時間
                    # }

                    # 構建訊息字典，包含所有可用字段
                    dict_ais_msg = {
                        'msg_type': ais_msg.msg_type,
                        'repeat': ais_msg.repeat,
                        'mmsi': ais_msg.mmsi,
                        'status': ais_msg.status.name if ais_msg.status else None,  # Enum類型轉為字串
                        'turn': ais_msg.turn if ais_msg.turn is not None else None,
                        'speed': ais_msg.speed,
                        'accuracy': ais_msg.accuracy,
                        'lon': ais_msg.lon,
                        'lat': ais_msg.lat,
                        'course': ais_msg.course,
                        'heading': ais_msg.heading,
                        'second': ais_msg.second,
                        'maneuver': ais_msg.maneuver.name if ais_msg.maneuver else None,  # Enum類型轉為字串
                        'spare_1': getattr(ais_msg.spare_1, 'spare_1', None),
                        'raim': ais_msg.raim,
                        'radio': ais_msg.radio,
                        # 靜態數據字段（如果存在，若無則為 None）************************************************
                        'ship_type': getattr(ais_msg, 'ship_type', None), # 船隻類型
                        'length': getattr(ais_msg, 'length', None), # 船隻長度
                        'width': getattr(ais_msg, 'width', None), # 船隻寬度
                        'call_sign': getattr(ais_msg, 'call_sign', None), # 船隻呼叫符號
                        'destination': getattr(ais_msg, 'destination', None), # 船隻目的地
                        'timestamp': getattr(ais_msg, 'timestamp', None), # 訊息的時間戳
                        'sog': getattr(ais_msg, 'sog', None), # 地面速度
                        'cog': getattr(ais_msg, 'cog', None), # 地面航向
                        'recv_ts': now_time.isoformat()  # 記錄接收時間
                    }

                    # 寫入 NDJSON 文件，每筆訊息一行
                    json.dump(dict_ais_msg, json_file, ensure_ascii=False)
                    json_file.write('\n')
                    json_file.flush()
                    print(f'紀錄時間: {now_time.isoformat()}')
                except Exception as e:
                    pass

            # 檢查是否過了一小時，若過了一小時則結束程式
            if (now_time - start_time) >= timedelta(hours=1):
                print(f"{(now_time - start_time)}內共接收到 {signal_count} 條訊息。")
                break

except KeyboardInterrupt:
    print("程序被手動終止，正在保存數據...")

finally:
    sock.close()  # 關閉 socket 連接
    print("連接已關閉")
