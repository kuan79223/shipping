import json
import re
import socket
from datetime import datetime, timedelta
from pyais.stream import SocketStream

# 抽出純 NMEA 行：!AIVDM/.../*HH 或 !AIVDO/.../*HH
NMEA_RE = re.compile(r'!(?:AIVDM|AIVDO),[^*\r\n]*\*[0-9A-Fa-f]{2}')

def extract_nmea(raw_str: str):
    """
    從任何字串中萃取出「純 NMEA 行」(含 *校驗碼)。
    例: "AISSentence<!AIVDM,...*1D>" -> "!AIVDM,...*1D"
    """
    m = NMEA_RE.search(raw_str)
    return m.group(0) if m else None

def validate_checksum(nmea_line: str) -> bool:
    """
    驗證 NMEA 校驗碼。nmea_line 必須已是純 NMEA 行（含 *HH）
    校驗範圍：從 '!' 之後到 '*' 之前的所有字元 XOR
    """
    try:
        head, cs_hex = nmea_line.split('*', 1)
        cs_hex = cs_hex[:2]  # 只取兩位十六進位校驗碼
        given = int(cs_hex, 16)
    except Exception:
        return False

    calc = 0
    for ch in head[1:]:  # 跳過起始 '!'
        calc ^= ord(ch)  # XOR
    return calc == given

def ais_savin_dict(ais_msg):
    return {
        'msg_type': ais_msg.msg_type,
        'repeat': ais_msg.repeat,
        'mmsi': ais_msg.mmsi,
        'status': getattr(ais_msg.status, 'name', None) if hasattr(ais_msg, 'status') else None,
        'turn': getattr(ais_msg, 'turn', None),
        'speed': getattr(ais_msg, 'speed', None),
        'accuracy': getattr(ais_msg, 'accuracy', None),
        'lon': getattr(ais_msg, 'lon', None),
        'lat': getattr(ais_msg, 'lat', None),
        'course': getattr(ais_msg, 'course', None),
        'heading': getattr(ais_msg, 'heading', None),
        'second': getattr(ais_msg, 'second', None),
        'maneuver': getattr(ais_msg.maneuver, 'name', None) if hasattr(ais_msg, 'maneuver') else None,
        'raim': getattr(ais_msg, 'raim', None),
        'radio': getattr(ais_msg, 'radio', None),
        'ship_type': getattr(ais_msg, 'ship_type', None),
        'length': getattr(ais_msg, 'length', None),
        'width': getattr(ais_msg, 'width', None),
        'call_sign': getattr(ais_msg, 'call_sign', None),
        'destination': getattr(ais_msg, 'destination', None),
        'timestamp': getattr(ais_msg, 'timestamp', None),
        'sog': getattr(ais_msg, 'sog', None),
        'cog': getattr(ais_msg, 'cog', None),
    }

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

with open("ais_data.ndjson", "a", encoding="utf-8") as json_file, \
     open("ais_log.txt", "a", encoding="utf-8") as txt_file, \
     open("ais_failed.txt", "a", encoding="utf-8") as fail_file, \
     open("ais_checksum_failed.txt", "a", encoding="utf-8") as checksum_file:
    try:
        for sentence in SocketStream(sock):
            if datetime.now() >= deadline:
                print("⏰ 時間到，停止接收")
                break

            raw_repr = str(sentence)          # 可能長成 AISSentence<!AIVDM,...*HH>
            nmea = extract_nmea(raw_repr)     # 抽出 !AIVDM/.../*HH

            total_received += 1
            # 只要抽到一條合法 NMEA，就算收到一筆 sentence
            if nmea:
                txt_file.write(nmea + "\n")   # 日誌用純 NMEA
                txt_file.flush()
            else:
                # 連 NMEA 都抽不到，直接記為校驗/格式類問題
                ais_checksum_failed += 1
                checksum_file.write(raw_repr + "  <-- 無法抽出 NMEA 行\n")
                checksum_file.flush()
                continue

            # 校驗碼驗證
            if not validate_checksum(nmea):
                ais_checksum_failed += 1
                checksum_file.write(nmea + "  <-- 校驗失敗/缺少校驗碼\n")
                checksum_file.flush()
                print(f"⚠️ 校驗失敗: {nmea}")
                continue

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
                print(f"✅ AIS 解碼成功 ({ais_complete}/{total_received})")

            except Exception as e:
                ais_failed += 1
                fail_file.write(f"{nmea if nmea else raw_repr}  <-- 解碼失敗: {e}\n")
                fail_file.flush()
                print(f"⚠️ 解碼失敗: {nmea if nmea else raw_repr} ({e})")

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
