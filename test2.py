import pyais
import socket
import json

def ais_savin_dict(ais_msg):

    # distance = haversine(ais_msg.lon, ais_msg.lat, TARGET_LON, TARGET_LAT)
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
        # 'distance': round(distance, 2),  # 與船舶中心的距離
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
        'cog': getattr(ais_msg, 'cog', None)  # 地面航向
        # 'recv_ts': now_time.isoformat() if now_time else None  # 記錄接收時間
    }

    return dict_ais_msg


buffer = b""  # 暫存區
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("192.168.2.1", 3333))

dict_ais_msg = dict()

try:
    with (open("ais_log.txt", "a", encoding="utf-8") as txt_file_write, \
        open("ais_data.ndjson", "a", encoding="utf-8") as json_file_write):

        while True:
            chunk = sock.recv(1024)
            if not chunk:
                break
            buffer += chunk # 先持續接收訊號

            # 判斷 buffer 裡有沒有完整的一行 (結尾 \r\n)
            while b"\r\n" in buffer:
                line, buffer = buffer.split(b"\r\n", 1)  # 拿一行出來，剩下的繼續留在 buffer
                line = line.decode("ascii", errors="ignore").strip()

                # 1️⃣ 判斷是不是 AIVDM
                if line.startswith("!AIVDM"):
                    print("收到 AIVDM 訊號:", line)

                    try:
                        msg = pyais.decode(line)
                        dict_ais_msg = ais_savin_dict(msg)
                        json.dump(dict_ais_msg, json_file_write, ensure_ascii=False)
                        json_file_write.write("\n")
                        json_file_write.flush()
                    except Exception as e:
                        print("⚠️ pyais 解碼失敗:", e)

                # 2️⃣ 其他 NMEA 訊號（可視情況記錄或丟掉）
                else:
                    # 例如 GNSS 資料
                    print("忽略非 AIS 訊號:", line)
                    txt_file_write.write(line + "\n")
                    txt_file_write.flush()

except KeyboardInterrupt:
    print("⚠️ 手動中止")

finally:
    sock.close()
