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

# 整合AIS 訊號
def is_complete_ais(str_msg):
    str_info = str_msg.strip()
    # 判斷字串訊息內有無「*」字
    if '*' not in str_info:
        return False

    # 找到 * 的位置，並確認 * 後面剛好有 2 個字元。依 NMEA 格式，* 後面必須跟著兩位 16 進位數字（校驗值）。
    star = str_info.rfind('*')
    print(f'找到 * 位置: {star}')

    if len(str_info) - star - 1 != 2:  # *HH (兩位 HEX)
        return False

    # 取出 * 後面的那兩個字元，檢查是否都是合法的 16 進位字元（0–9, A–F, a–f）。
    chk = str_info[star+1:]
    # 字串內每個結果都是 True 才會 return True
    return all(c in '0123456789abcdefABCDEF' for c in chk)

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

def bytes_stream_to_lines(byte_chunks):
    """把 socket chunk 切成行：支援 \r\n / \n / \r"""
    carry = ""
    for chunk in byte_chunks:
        text = chunk.decode("ascii", errors="ignore")
        text = text.replace("\r", "\n")
        parts = (carry + text).split("\n")
        *full, carry = parts
        for line in full:
            yield line
    if carry:
        yield carry  # 末尾殘段（可能不完整）

# ====== 範例：從 socket 讀取、過濾並解碼到 NDJSON ======
def run_socket_reader(host="192.168.2.1", port=3333, out_ndjson="ais_data.ndjson", out_raw="ais_raw_log.txt", run_hours=1):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    connect_time = datetime.now()  # 連線建立時間（程式開始跑的時間）
    deadline = connect_time + timedelta(minutes=1)

    first_ais_time = None  # 第一筆完整 AIS 收到時間
    ais_complete = 0  # 完整 AIS 句數（含解碼失敗）

    print(f"{connect_time} Start...")

    try:
        with open(out_ndjson, "a", encoding="utf-8") as json_file_write, \
                open(out_raw, "a", encoding="utf-8") as raw_file_write:
            total_chunks = 0
            # socket主要迴圈
            def chunk_iter():
                nonlocal total_chunks  # 告訴 Python 這個變數是用外層函式的
                while True:
                    # 時間到就停止
                    if datetime.now() >= deadline:
                        break
                    data = sock.recv(4096)
                    print(data.decode('ascii', errors='ignore').strip())
                    if not data:
                        break
                    text = data.decode("ascii", errors="ignore")
                    # 確保每次寫入都只有一個換行，不會多空行
                    if not text.endswith("\n"):
                        text += "\n"

                    raw_file_write.writelines(text)
                    raw_file_write.flush()
                    total_chunks += 1

                    yield data

            line_iter = bytes_stream_to_lines(chunk_iter())

            for nmea in iter_complete_ais_from_text(line_iter):

                # 只會是 !AIVDM/!AIVDO 完整句子
                try:
                    ais_msg = pyais.decode(nmea)  # pyais 解析
                    # print(f'解碼: {ais_msg}')
                    # 記錄第一筆 AIS 的時間
                    if first_ais_time is None:
                        first_ais_time = datetime.now()

                    now_time = datetime.now()  # 每筆 AIS 收到的時間
                    dict_ais_msg = ais_savin_dict(ais_msg, now_time=now_time)
                    json.dump(dict_ais_msg, json_file_write, ensure_ascii=False)
                    json_file_write.write('\n')
                    json_file_write.flush()
                    ais_complete += 1  # ← 每筆完整 AIS 就 +1

                except Exception as e:
                    # 校驗錯或解不開就跳過（可視需要記錄）
                    # print("Decode fail:", e, nmea)
                    pass
    except KeyboardInterrupt:
        print("⚠️ 手動中止")
    finally:
        sock.close()
        end_time = datetime.now()
        print("連線已關閉")
        # 總結資訊
        print("===== Summary =====")
        print(f"Connect start : {connect_time}")
        print(f"First AIS     : {first_ais_time if first_ais_time else 'N/A (no AIS received)'}")
        print(f"End time      : {end_time}")
        print(f"Run duration  : {end_time - connect_time}")
        print(f"共接收 {total_chunks} 個 recv chunk，已寫入 {out_raw}")
        print(f"AIS complete  : {ais_complete}, Output file   : {out_ndjson}")

        # ---- 安全讀回 NDJSON 並輸出 Excel/CSV ----
        try:
            if os.path.exists(out_ndjson) and os.path.getsize(out_ndjson) > 0:
                df = pd.read_json(out_ndjson, lines=True)
                base, _ = os.path.splitext(out_ndjson)  # 去掉原始副檔名

                df.to_excel(f"{base}.xlsx", index=False)
                print("已將 NDJSON 轉換為 Excel")
            else:
                print("NDJSON 是空的，略過讀取/轉換。")

        except ValueError as e:
            # 內容不是合法 NDJSON（例如混入非 JSON 行）
            print(f"讀取 NDJSON 失敗：{e}。請檢查檔案內容是否每行皆為有效 JSON。")

# ====== 若改成從檔案讀取 ======
def run_file_reader(input_txt="sent_ais.txt", out_ndjson="test_ais_data.ndjson"):
    with open(input_txt, "r", encoding="utf-8") as file_read, open(out_ndjson, "a", encoding="utf-8") as json_file_write:
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

    run_socket_reader(host=HOST, port=PORT, out_ndjson="ais_output.ndjson",  run_hours=1)
    # run_file_reader(input_txt="sent_ais.txt", out_ndjson="test_ais_output.ndjson")
