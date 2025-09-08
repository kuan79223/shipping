import json
from pyais.stream import SocketStream
import socket
from datetime import datetime, timedelta


def ais_savin_dict(ais_msg):
    """轉換 AIS 訊息成 dict 格式"""
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
        # 靜態資料（若有的話）
        'ship_type': getattr(ais_msg, 'ship_type', None),
        'length': getattr(ais_msg, 'length', None),
        'width': getattr(ais_msg, 'width', None),
        'call_sign': getattr(ais_msg, 'call_sign', None),
        'destination': getattr(ais_msg, 'destination', None),
        'timestamp': getattr(ais_msg, 'timestamp', None),
        'sog': getattr(ais_msg, 'sog', None),
        'cog': getattr(ais_msg, 'cog', None)
    }


print("🚢 Start receiving AIS messages...")

# 統計計數器
total_received = 0  # 收到的 sentence 總數
ais_complete = 0    # 成功解碼的數量
ais_failed = 0      # 解碼失敗數量

# === 建立 TCP socket 連線 ===
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("192.168.2.1", 3333))
# 設定接收 5 分鐘
start_time = datetime.now()
deadline = start_time + timedelta(minutes=5)

print("Start receiving...")

with open("ais_data.ndjson", "a", encoding="utf-8") as json_file, \
    open("ais_log.txt", "a", encoding="utf-8") as txt_file, \
    open("ais_failed.txt", "a", encoding="utf-8") as fail_file:
    try:
        # 直接從 TCP 讀取並解碼
        for sentence in SocketStream(sock):
            # 若超過 5 分鐘，跳出迴圈
            if datetime.now() >= deadline:
                print("⏰ 時間到，停止接收")
                break
            print(sentence)
            total_received += 1  # 不管能不能解碼，都算收到一次

            raw_str = str(sentence)  # 原始 NMEA sentence（含 !AIVDM,...,*hh）
            txt_file.write(raw_str + "\n")  # 存到 txt 檔
            txt_file.flush()

            try:
                msg = sentence.decode()  # ⭐ 關鍵步驟
                if msg is None:
                    # pyais 有可能回傳 None（代表還在等後續片段）
                    ais_failed += 1
                    fail_file.write(raw_str + "  <-- 未完成 (None)\n")
                    fail_file.flush()
                    print(f"⚠️ 解碼未完成 (已收到 {total_received} 筆)")
                    continue

                dict_msg = ais_savin_dict(msg)
                json.dump(dict_msg, json_file, ensure_ascii=False)
                json_file.write("\n")
                json_file.flush()
                ais_complete += 1
                print(f"✅ AIS 解碼成功 ({ais_complete}): {dict_msg}")
            except Exception as e:
                ais_failed += 1
                fail_file.write(raw_str + f"  <-- 解碼失敗: {e}\n")
                fail_file.flush()
                print(f"⚠️ 解碼失敗 (已收到 {total_received} 筆):", e)

    except KeyboardInterrupt:
        print("⚠️ 手動中止")

    finally:
        sock.close()
        print("===== Summary =====")
        print(f"總共收到 Sentence 數: {total_received}")
        print(f"成功解碼數: {ais_complete}")
        if total_received > 0:
            receive_rate = (ais_complete / total_received) * 100
            print(f"接收率: {receive_rate:.2f}%")
        else:
            print("⚠️ 沒有收到任何資料")