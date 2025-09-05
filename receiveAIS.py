import pyais
import socket
from datetime import datetime, timedelta
import math
import json
import os
import pandas as pd

HOST = '192.168.2.1'  # 設定為伺服器的IP
PORT = 3333  # 設定端口

AIS_STARTS = ('!AIVDM', '!AIVDO')
# 目標位置（例如辦公室的位置）
TARGET_LON = 120.29207  # 目標經度
TARGET_LAT = 22.63035  # 目標緯度

# ***************************************************************************


class ReceiveAIS(object):

    def __init__(self, host="192.168.2.1", port=3333, save_ndjson="ais_data.ndjson", log_txt="ais_raw_log.txt", run_mins=5):

        self.host = host
        self.port = port
        self.save_ndjson = save_ndjson
        self.log_txt = log_txt
        self.run_mins = run_mins
        self.error_file = 'ais_decode_errors.txt'

    # 以 socket 收 AIS 訊號
    def run_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))

        connect_time = datetime.now()
        deadline = connect_time + timedelta(minutes=self.run_mins)
        first_ais_time = None
        ais_complete = 0
        total_chunks = 0

        print(f"{connect_time} Start...")
        buffer_str = ""  # 用來累積不完整的 AIS 訊息
        try:
            with open(self.save_ndjson, "a", encoding="utf-8") as json_file_write, \
                    open(self.log_txt, "a", encoding="utf-8") as txt_file_write, \
                    open(self.error_file, "a", encoding="utf-8") as error_file:  # 記錄解碼錯誤
                while datetime.now() < deadline:
                    data = sock.recv(4096)
                    if not data:
                        break
                    text = data.decode("ascii", errors="ignore")
                    if not text.endswith("\n"):
                        text += "\n"
                    txt_file_write.write(text)
                    txt_file_write.flush()
                    total_chunks += 1

                    # 將 chunk 拆行，逐行處理
                    lines = text.replace("", "\n").split("\n")
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        # 若碰到新的 AIS 訊號 !AIVDM ; !AIVDO 開頭，重置 buffer
                        if line.startswith(AIS_STARTS):
                            if buffer_str:  # 若前一條訊息存在，檢查是否為完整訊息
                                # 檢查上一條訊息是否完整
                                if is_complete_ais(buffer_str):
                                    ais_msg = pyais.decode(buffer_str)  # 解碼訊息
                                    ais_complete += 1
                                    dict_ais_msg = ais_savin_dict(ais_msg, now_time=datetime.now())
                                    json.dump(dict_ais_msg, json_file_write, ensure_ascii=False)
                                    json_file_write.write("\n")
                                    json_file_write.flush()
                            buffer_str = line
                        else:
                            buffer_str += line  # 累積可能跨行的訊息
                            print(f'字串相加 {buffer_str}')

                        # 判斷是否完整
                        if is_complete_ais(buffer_str):
                            try:
                                ais_msg = pyais.decode(buffer_str)
                                if first_ais_time is None:
                                    first_ais_time = datetime.now()
                                now_time = datetime.now()
                                dict_ais_msg = ais_savin_dict(ais_msg, now_time)

                                # 直接寫入 NDJSON
                                json.dump(dict_ais_msg, json_file_write, ensure_ascii=False)
                                json_file_write.write("\n")
                                json_file_write.flush()

                                ais_complete += 1
                            except Exception as e:
                                # 解碼錯誤記錄 xxxxxxxxxxxxxxxxxxxxxxxx
                                error_file.write(f"{buffer_str}\n")
                                buffer_str = ""  # 清空 buffer，準備下一條訊息

        except KeyboardInterrupt:
            print("⚠️ 手動中止")
        finally:
            sock.close()
            end_time = datetime.now()
            print("連線已關閉")
            print("===== Summary =====")
            print(f"Connect start : {connect_time}")
            print(f"First AIS     : {first_ais_time if first_ais_time else 'N/A (no AIS received)'}")
            print(f"End time      : {end_time}")
            print(f"Run duration  : {end_time - connect_time}")
            print(f"共接收 {total_chunks} 個 recv chunk，已寫入 {self.log_txt}")
            print(f"AIS complete  : {ais_complete}, Output file   : {self.save_ndjson}")

            # 將 NDJSON 轉 Excel
            try:
                if os.path.exists(self.save_ndjson) and os.path.getsize(self.save_ndjson) > 0:
                    df = pd.read_json(self.save_ndjson, lines=True)
                    base, _ = os.path.splitext(self.save_ndjson)
                    df.to_excel(f"{base}.xlsx", index=False)
                    print("已將 NDJSON 轉換為 Excel")
                else:
                    print("NDJSON 是空的，略過轉換")
            except ValueError as e:
                print(f"讀取 NDJSON 失敗：{e}")

    # ====== 若改成從檔案讀取 ======
    def run_file_reader(self, input_txt="sent_ais.txt", out_ndjson="test_ais_data.ndjson"):
        with open(self, input_txt, "r", encoding="utf-8") as file_read, open(out_ndjson, "a",
                                                                       encoding="utf-8") as json_file_write:
            for nmea in iter_complete_ais_from_text(file_read):
                if nmea.startswith(AIS_STARTS):
                    try:
                        ais_msg = pyais.decode(nmea)
                        now_time = datetime.now()  # 每筆 AIS 收到的時間

                        dict_ais_msg = ais_savin_dict(ais_msg, now_time=now_time)
                        json.dump(dict_ais_msg, json_file_write, ensure_ascii=False)
                        json_file_write.write('\n')
                        json_file_write.flush()

                    except Exception:
                        pass

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

# 判斷 字串最後面校正碼 是否正確
def is_complete_ais(str_msg):
    str_info = str_msg.strip()
    # 檢查 * 字符後面的 校驗碼 部分是否符合 NMEA 訊息的格式
    if '*' not in str_info:
        return False
    # 返回 '*' 後的索引位置
    star = str_info.rfind('*')
    # 從字串 '*' 右邊開始找，後面剛好有 2 個字元。依 NMEA 格式，* 後面必須跟著兩位 16 進位數字（校驗值）。
    if len(str_info) - star - 1 != 2:  # *HH (兩位 HEX)
        return False
    # 取出 * 面的那兩個字元，檢查是否都是合法的 16 進位字元（0–9, A–F, a–f）。
    chk = str_info[star+1:]
    # 字串內每個結果都是 True 才會 return True
    return all(c in '0123456789abcdefABCDEF' for c in chk)

# 用在讀取文字檔
def iter_complete_ais_from_text(lines_iterable):
    str_buf = ''
    buffer_flag = False

    for raw in lines_iterable:
        line = raw.strip()
        if not line:
            continue
        if line.startswith(AIS_STARTS):
            str_buf = line
            buffer_flag = True
        else:
            if buffer_flag:
                str_buf += line
                print(f'字串相加 {str_buf}')
            else:
                continue
        # 每次遇到 yield，會把一個值丟出去，但函式本身不會結束。
        # 下一次再呼叫時，它會從上次停下來的地方繼續跑。
        # 這樣就能一行一行處理資料（例如 AIS 訊息）。
        if is_complete_ais(str_buf):
            yield str_buf
            str_buf = ''
            buffer_flag = False


def ais_savin_dict(ais_msg, now_time=None):

    distance = haversine(ais_msg.lon, ais_msg.lat, TARGET_LON, TARGET_LAT)
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
        'distance': round(distance, 2),  # 與船舶中心的距離
        'course': ais_msg.course,
        'heading': ais_msg.heading,
        'second': ais_msg.second,
        'maneuver': ais_msg.maneuver.name if ais_msg.maneuver else None,  # Enum類型轉為字串
        'spare_1': getattr(ais_msg.spare_1, 'spare_1', None),
        'raim': ais_msg.raim,
        'radio': ais_msg.radio,
        # 靜態數據字段（如果存在，若無則為 None）************************************************
        'ship_type': getattr(ais_msg, 'ship_type', None),  # 船隻類型
        'length': getattr(ais_msg, 'length', None),  # 船隻長度
        'width': getattr(ais_msg, 'width', None),  # 船隻寬度
        'call_sign': getattr(ais_msg, 'call_sign', None),  # 船隻呼叫符號
        'destination': getattr(ais_msg, 'destination', None),  # 船隻目的地
        'timestamp': getattr(ais_msg, 'timestamp', None),  # 訊息的時間戳
        'sog': getattr(ais_msg, 'sog', None),  # 地面速度
        'cog': getattr(ais_msg, 'cog', None),  # 地面航向
        'recv_ts': now_time.isoformat() if now_time else None  # 記錄接收時間
    }
    return dict_ais_msg


if __name__ == '__main__':

    receiveAIS = ReceiveAIS(host=HOST, port=PORT, save_ndjson="ais_output.ndjson",  run_mins=5)
    receiveAIS.run_socket()

    # run_file_reader(input_txt="sent_ais.txt", out_ndjson="test_ais_output.ndjson")
