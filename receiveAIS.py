import json
import socket
import pyais  # 這是為了解析 AIS 訊息 Type 1–27
from datetime import datetime, timedelta
import math

# 哈弗辛公式
def haversine(lon1, lat1, lon2, lat2):
    # 地球半徑 (公里)
    R = 6371.0
    # 將經緯度從度數轉換為弧度
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    # 計算經度和緯度的差異
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    # 哈弗辛公式
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    # 計算距離
    distance = R * c  # 距離（公里）
    return distance


host = '192.168.2.1'  # 設定為伺服器的IP
port = 3333  # 設定端口

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))

# 紀錄訊號數量
signal_count = 0
start_time = datetime.now()  # 程式開始時間

filename = 'ais_data_24V'
LOG_PATH = f'{filename}.ndjson'  # 設定 NDJSON 檔案儲存 AIS 訊息

# 目標位置（例如辦公室的位置）
TARGET_LON = 120.29207  # 目標經度
TARGET_LAT = 22.63035  # 目標緯度

# 確保一次讀取完整訊息
buffer_size = 4096  # 設定適合的緩衝區大小  1024 = 1KB
# 用來儲存接收到的訊息
message = ''
# 設定 .txt 檔案儲存接收到的訊息
txt_file = 'received_ais_messages.txt'

try:
    with (open(txt_file, 'a', encoding='utf-8') as txt_file, \
    open(LOG_PATH, 'a', encoding='utf-8') as json_file):

        print(f'{start_time} Start...')
        while True:
            # 記錄本次接收的時間戳（台北時間）
            now_time = datetime.now()
            # 去除首尾空格
            chunk = sock.recv(buffer_size).decode('ascii', errors='ignore').strip()
            print(chunk)

            signal_count += 1
            list_chunk = chunk.split(',')

            # 檢查第二個欄位的值
            if list_chunk[0] == '!AIVDM':
                if len(list_chunk) > 1 and list_chunk[1] != ' ':
                    if message == '':  # 如果訊息還是空的，表示新訊息開始
                        message = chunk
                    else:
                        message += chunk
                        print(f'串字輸出: {message}')

                elif int(list_chunk[1]) > 1:
                    message += chunk
                    print(f'大於1 繼續串字: {message}')

            if len(message) > 3 and message[-3] == '*':
                message += chunk
                print(f'完整訊號: {message}')
                txt_file.write(message)
                message = ''
                break

#             if line.startswith('!AIVDM'):
#                 # 每接收一條訊息，就更新訊號數量
#                 try:
#                     # 將收到的訊號解碼
#                     ais_msg = pyais.decode(line.encode('utf-8'))
#                     print(f'解碼訊號: {ais_msg}')
#
#                     # 計算兩者之間的距離
#                     distance = haversine(ais_msg.lon, ais_msg.lat, TARGET_LON, TARGET_LAT)
#                     # print(f"船隻與目標位置的距離是：{round(distance, 2)} 公里")
#
#                     # 構建訊息字典，包含所有可用字段
#                     dict_ais_msg = {
#                         'msg_type': ais_msg.msg_type,
#                         'repeat': ais_msg.repeat,
#                         'mmsi': ais_msg.mmsi,
#                         'status': ais_msg.status.name if ais_msg.status else None,  # Enum類型轉為字串
#                         'turn': ais_msg.turn if ais_msg.turn is not None else None,
#                         'speed': ais_msg.speed,
#                         'accuracy': ais_msg.accuracy,
#                         'lon': ais_msg.lon,
#                         'lat': ais_msg.lat,
#                         'distance': round(distance, 2), # 與船舶中心的距離
#                         'course': ais_msg.course,
#                         'heading': ais_msg.heading,
#                         'second': ais_msg.second,
#                         'maneuver': ais_msg.maneuver.name if ais_msg.maneuver else None,  # Enum類型轉為字串
#                         'spare_1': getattr(ais_msg.spare_1, 'spare_1', None),
#                         'raim': ais_msg.raim,
#                         'radio': ais_msg.radio,
#                         # 靜態數據字段（如果存在，若無則為 None）************************************************
#                         'ship_type': getattr(ais_msg, 'ship_type', None), # 船隻類型
#                         'length': getattr(ais_msg, 'length', None), # 船隻長度
#                         'width': getattr(ais_msg, 'width', None), # 船隻寬度
#                         'call_sign': getattr(ais_msg, 'call_sign', None), # 船隻呼叫符號
#                         'destination': getattr(ais_msg, 'destination', None), # 船隻目的地
#                         'timestamp': getattr(ais_msg, 'timestamp', None), # 訊息的時間戳
#                         'sog': getattr(ais_msg, 'sog', None), # 地面速度
#                         'cog': getattr(ais_msg, 'cog', None), # 地面航向
#                         'recv_ts': now_time.isoformat()  # 記錄接收時間
#                     }
#
#                     # 寫入 NDJSON 文件，每筆訊息一行
#                     json.dump(dict_ais_msg, json_file, ensure_ascii=False)
#                     json_file.write('\n')
#                     json_file.flush()
#                     # print(f'紀錄時間: {now_time.isoformat()}')
#                 except Exception as e:
#                     pass
#
#             print(line)
#             if (now_time - start_time) >= timedelta(hours=1): # 檢查是否過了一小時，若過了一小時則結束程式
#             # if (now_time - start_time) >= timedelta(minutes=10): # 檢查是否過了 10 分鐘，若過了 10 分鐘則結束程式
#                 print(f"{(now_time - start_time)}內共接收到 {signal_count} 條訊息。")
#                 break
#
except KeyboardInterrupt:
    print("程序被手動終止，正在保存數據...")
    print(f"{(now_time - start_time)}內共接收到 {signal_count} 條訊息。")

finally:
    sock.close()  # 關閉 socket 連接
    print("連接已關閉")
    # 轉成 excel
    import pandas as pd

    # 讀取 NDJSON 文件
    ndjson_file = f'{filename}.ndjson'  # 假設你的 NDJSON 文件名為 ais_data_12V_part1.ndjson
    df = pd.read_json(ndjson_file, lines=True)

    # 將資料保存為 Excel 格式
    df.to_excel(f'{filename}.xlsx', index=False)

    print("已將 NDJSON 轉換為 Excel")
