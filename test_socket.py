import socket
import pyais
import json
from datetime import datetime, timedelta


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


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("192.168.2.1", 3333))
connect_time = datetime.now()

deadline = connect_time + timedelta(minutes=5)

print("Start...")
ls_msg = list()

buffer_msg = ''
flag_VDM = False

total_msg = 0
ais_complete = 0

dict_ais_msg = dict()
dict_msg_parts = dict()
fragmented_msgs = dict()

try:
    with open("ais_log.txt", "a", encoding="utf-8") as txt_file_write, \
        open("ais_data.ndjson", "a", encoding="utf-8") as json_file_write:

        # while datetime.now() < deadline:
        while True:
            text = sock.recv(1024) # 括號內為字數值  256 / 8 = 32
            # print(text.__class__)  #　bytes
            # print(str(text))  # b'A,M,1,,,,,,,,,,,,,99.99,99.99,99.99*22\r\n'
            if not text:
                break
            total_msg += 1
            # # 去除二進制寫入txt
            ais_ascii = text.decode("ascii")
            # print(ascii_msg)
            # print(' ------------------------- ')
            txt_file_write.writelines(str(text))
            txt_file_write.flush()
            # print(ascii_msg.__class__) # str
            # print(ascii_msg)
            parts = ais_ascii.split(',')
            print(parts)
            # 假如完整句子直接解碼
            if parts[1] == '1' and text.startswith(b'!AIVDM') and text.endswith(b'\r\n'):
                ascii_msg = text.decode('ascii')
                decode_ais = pyais.decode(ascii_msg.replace('\r\n', ''))

                print(f'完整句子直接解碼 :{ascii_msg}')

                dict_ais_msg = ais_savin_dict(decode_ais)
                json.dump(dict_ais_msg, json_file_write, ensure_ascii=False)
                json_file_write.write('\n')
                json_file_write.flush()
                ais_complete += 1  # ← 每筆完整 AIS 就 +1
            # 起頭給狀態
            elif len(parts) > 1 and text.startswith(b'!AIVDM'):
                buffer_msg = text
                flag_VDM = True
                # buffer_msg = ascii_msg
                print(f'句子的頭部是AIVDM :{buffer_msg}')
                fragment_number = int(parts[2])
                total_fragments = int(parts[1])

                # Store the fragments in a dictionary
                if fragment_number not in fragmented_msgs:
                    fragmented_msgs[fragment_number] = []

                # Add the fragment data to the dictionary
                fragmented_msgs[fragment_number].append(parts[4])

            # 需要有 AIVDM 與 換行
            elif flag_VDM and text.endswith(b'\r\n'):
                buffer_msg += text
                ascii_msg = buffer_msg.decode('ascii').replace('\r\n', '')
                decode_ais = pyais.decode(ascii_msg)
                print(f'得到換行符號句子 {buffer_msg}, \n進行解碼 :{decode_ais}')
                flag_VDM = False

                dict_ais_msg = ais_savin_dict(decode_ais)
                json.dump(dict_ais_msg, json_file_write, ensure_ascii=False)
                json_file_write.write('\n')
                json_file_write.flush()
                ais_complete += 1  # ← 每筆完整 AIS 就 +1

            # 找不到換行，繼續串
            elif flag_VDM:
                buffer_msg += text


except KeyboardInterrupt:
    print("⚠️ 手動中止")

finally:
    sock.close()
    end_time = datetime.now()
    print("連線已關閉")
    print("===== Summary =====")
    print(f"Connect start : {connect_time}")
    print(f"End time      : {end_time}")
    print(f"Run duration  : {end_time - connect_time}")
    # print(f"共接收 {total_chunks} 個 recv chunk，已寫入 {self.log_txt}")
    print(f"AIS complete  : {ais_complete}")
