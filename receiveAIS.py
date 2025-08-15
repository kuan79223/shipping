import json
import socket
import pyais  # 這是為了解析 AIS 訊息
from datetime import datetime, timedelta
from collections import deque

host = '192.168.2.1'  # 設定為伺服器的IP
port = 3333  # 設定端口

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))

# 模擬多筆 AIS 訊息
list_ais_data = list()

# 記錄過去一小時內接收到的訊號數量
window = deque()  # 用來儲存時間戳
WINDOW_LEN = timedelta(hours=1) # 定義過去一小時的時間範圍

# 設定 NDJSON 檔案儲存 AIS 訊息
LOG_PATH = "ais_data.ndjson"


# 函數：移除過期的訊號（超過 1 小時的）
def prune(now: datetime):
    cutoff = now - WINDOW_LEN
    # window 為雙向序列, 當 window 的時間比前一小時前的時間 cut_off
    while window and window[0] < cutoff:
        window.popleft() # 彈出序列左邊的元素

try:
    print('Start...')
    with open(LOG_PATH, 'a', encoding='utf-8') as json_file:
        while True:
            line = sock.recv(1024).decode('ascii', errors='ignore').strip()
            if line.startswith('!AIVDM'):
                try:
                    # 將收到的訊號解碼
                    ais_msg = pyais.decode(line.encode('utf-8'))
                    print(f'解碼訊號: {ais_msg}')
                    # 記錄本次接收的時間戳（台北時間）
                    # now = datetime.now()
                    now = datetime.now().replace(microsecond=0)  # 去除微秒部分
                    window.append(now)
                    prune(now)

                    # 將訊息轉換為字典格式
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
                        'spare_1': getattr(ais_msg.spare_1, 'spare_1', None),
                        'raim': ais_msg.raim,
                        'radio': ais_msg.radio,
                        'recv_ts': now  # 直接使用 datetime 物件
                        # 'recv_ts': now.isoformat()  # 記錄接收時間

                    }

                    # 寫入 NDJSON 文件，每筆訊息一行
                    json.dump(dict_ais_msg, json_file, ensure_ascii=False)
                    json_file.write('\n')
                    json_file.flush()

                    # 每10秒鐘報告一次過去 1 小時內的訊號數量
                    if len(window) % 10 == 0:
                        print(f"過去 1 小時接收到 {len(window)} 筆訊號")

                except Exception as e:
                    pass

except KeyboardInterrupt:
    print("程序被手動終止，正在保存數據...")

finally:
    sock.close()  # 關閉 socket 連接
    print("連接已關閉")
