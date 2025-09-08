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
dict_fragment = dict()

try:
    with (open("ais_log.txt", "a", encoding="utf-8") as txt_file_write, \
        open("ais_data.ndjson", "a", encoding="utf-8") as json_file_write):

        # while datetime.now() < deadline:
        while True:
            text = sock.recv(1024) # 括號內為字數值  256 / 8 = 32
            print(text)
            print()
            # print(text.__class__)  #　bytes
            # print(str(text))  # b'A,M,1,,,,,,,,,,,,,99.99,99.99,99.99*22\r\n'
            if not text:
                break
            total_msg += 1
            # # 去除二進制寫入txt
            ais_ascii = text.decode("ascii")
            # print(ascii_msg)
            # print(' ------------------------- ')
            # print(ascii_msg.__class__) # str
            # print(ascii_msg)
            txt_file_write.writelines(str(text))
            txt_file_write.flush()

            # 必須先有 AIVDM 訊號
            if text.startswith(b'!AIVDM'):
                ais_ascii = text.decode("ascii")
                parts = ais_ascii.split(',')
                total_fragments = int(parts[1])  # 總共訊息數
                current_fragment = int(parts[2])  # 目前是第幾個訊息

                print('收到 AIVDM 訊號 -------------')
                flag_VDM = True
                buffer_msg = text

                if flag_VDM and text.endswith(b'\r\n'):
                    buffer_msg += text
                    print(f'完整句子直接解碼 :{text}')
                    decode_ais = pyais.decode(ais_ascii.replace('\r\n', ''))
                    dict_ais_msg = ais_savin_dict(decode_ais)
                    json.dump(dict_ais_msg, json_file_write, ensure_ascii=False)
                    json_file_write.write('\n')
                    json_file_write.flush()
                    ais_complete += 1  # ← 每筆完整 AIS 就 +1
                    flag_VDM = False
                    break
                # 在狀態之下，繼續串文字
                elif flag_VDM:
                    buffer_msg += text
                    print(f'沒有遇到 \r\n 繼續串文字 :{buffer_msg}')

                # 不是完整句子判斷AIVDM起頭給狀態
                # if fragment_number >= 2:

                #     # Store the fragments in a dictionary
                #     if current_fragment not in dict_fragment:
                #         dict_fragment[current_fragment] = []

                #     # Add the fragment data to the dictionary
                #     dict_fragment[current_fragment].append(parts[5])
                    #
                    # elif flag_VDM and fragment_number == 1:
                    #     if text.endswith(b'\r\n'):
                    #      pass


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
