import json
import re
import socket
import math
import os
from datetime import datetime, timedelta

import pandas as pd
from pyais.stream import SocketStream

# 目標位置（例如辦公室的位置）
TARGET_LON = 120.29207  # 目標經度
TARGET_LAT = 22.63035  # 目標緯度

SAVE_NDJSON = 'ais_data.ndjson'
SAVE_LOG_TXT = 'ais_log.txt'
SAVE_LOG_FAILED_TXT ='ais_checksum_failed.txt'
SAVE_LOG_EXCEPT_TXT = 'ais_failed.txt'

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

def ais_savin_dict(ais_msg):
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
        'cog': getattr(ais_msg, 'cog', None)   # 地面航向
    }
    return dict_ais_msg


# 這裡要加反斜線 \，因為 * 在正則裡本來有特殊意義。
NMEA_RE = re.compile(r'!(?:AIVDM|AIVDO),[^*\r\n]*\*[0-9A-Fa-f]{2}')

# def extract_nmea(raw_str: str):
#     """
#     從任何字串中萃取出「純 NMEA 行」(含 *校驗碼)。
#     例: "AISSentence<!AIVDM,...*1D>" -> "!AIVDM,...*1D"
#     """
#     m = NMEA_RE.search(raw_str)
#     # print(m)
#     return m.group(0) if m else None
#
#
# def validate_checksum(nmea_line: str) -> bool:
#     """
#     驗證 NMEA 校驗碼。nmea_line 必須已是純 NMEA 行（含 *HH）
#     校驗範圍：從 '!' 之後到 '*' 之前的所有字元 XOR
#     """
#     try:
#         head, cs_hex = nmea_line.split('*', 1)
#         cs_hex = cs_hex[:2]  # 取星號後的兩位數字，轉成 16 進制整數
#         given = int(cs_hex, 16)
#     except Exception:
#         return False
#
#     calc = 0
#     for ch in head[1:]:  # 跳過起始 '!'
#         calc ^= ord(ch)  # XOR
#     return calc == given

# 原來寫入 txt 檔案用的
def sentence_to_raw_line(sentence) -> str:
    """
    安全取得原始 NMEA 行（可能只有一行，也可能多行）。
    優先走公開屬性；沒有就退回用正則從 str(sentence) 全抓。
    """
    # 一些版本會有 .line 或 .raw（bytes）
    if hasattr(sentence, 'line') and isinstance(sentence.line, str):
        return sentence.line.strip()
    if hasattr(sentence, 'raw') and isinstance(sentence.raw, (bytes, bytearray)):
        return sentence.raw.decode('ascii', 'ignore').strip()

    # 退而求其次：從字串表示抽出所有 NMEA 行
    s = str(sentence)
    # 可能包含兩行（你前面看到的情況），用 finditer 全抓
    matches = [m.group(0) for m in NMEA_RE.finditer(s)]
    return '\n'.join(matches) if matches else s.strip()

# ================================= main =========================================
print("🚢 Start receiving AIS messages...")

total_received = 0
ais_complete = 0
ais_failed = 0              # 其他解碼失敗（非校驗問題）
ais_checksum_failed = 0     # 校驗失敗/缺少校驗碼/抽不到 NMEA

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("192.168.2.1", 3333))
# sock.settimeout(10)  # 可選：避免長時間卡住

start_time = datetime.now()
deadline = start_time + timedelta(minutes=5)

print("Start receiving...")

with (open(SAVE_NDJSON, "a", encoding="utf-8") as json_file, \
     open(SAVE_LOG_TXT, "a", encoding="utf-8") as txt_file, \
    open(SAVE_LOG_FAILED_TXT, "a", encoding="utf-8") as checksum_file, \
    open(SAVE_LOG_EXCEPT_TXT, "a", encoding="utf-8") as fail_file,):
    try:
        for sentence in SocketStream(sock):
            if datetime.now() >= deadline:
                print("⏰ 時間到，停止接收")
                break
            total_received += 1
            # ********************************************
            # 1) 先把原始 NMEA 行完整寫入（可能 1 行或多行）
            raw_block = sentence_to_raw_line(sentence)
            print(raw_block)
            if raw_block:
                # 若內含多行，逐行寫入
                for ln in raw_block.splitlines():
                    if ln.strip():
                        txt_file.write(ln.strip() + "\n")
                txt_file.flush()
            # ********************************************
            # 解碼
            try:
                msg = sentence.decode()
                if msg is None:
                    # 多段訊息尚未收齊，由 pyais 內部等待，這裡不記 failed
                    continue

                dict_msg = ais_savin_dict(msg)
                json.dump(dict_msg, json_file, ensure_ascii=False)
                json_file.write("\n")
                json_file.flush()
                ais_complete += 1
                # print(f"✅ AIS 解碼成功 ({ais_complete}/{total_received})")

            except Exception as e:
                ais_failed += 1
                fail_file.write(f"{msg}  <-- 解碼失敗: {e}\n")
                fail_file.flush()
                print(f"⚠️ 解碼失敗: {msg} ({e})")

    except KeyboardInterrupt:
        print("⚠️ 手動中止")

    finally:
        sock.close()
        print("===== Summary =====")
        print(f"總共收到 Sentence 數: {total_received}")
        print(f"成功解碼數: {ais_complete}")
        print(f"校驗失敗/缺少校驗碼/格式不符: {ais_checksum_failed}")
        if total_received > 0:
            rate = (ais_complete / total_received) * 100
            print(f"接收率: {rate:.2f}%")
        else:
            print("⚠️ 沒有收到任何資料")

    # 將 NDJSON 轉 Excel
    try:
        if os.path.exists(SAVE_NDJSON) and os.path.getsize(SAVE_NDJSON) > 0:
            df = pd.read_json(SAVE_NDJSON, lines=True)
            base, _ = os.path.splitext(SAVE_NDJSON)
            df.to_excel(f"{base}.xlsx", index=False)
            print("已將 NDJSON 轉換為 Excel")
        else:
            print("NDJSON 是空的，略過轉換")
    except ValueError as e:
        print(f"讀取 NDJSON 失敗：{e}")