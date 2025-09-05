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

dict_ais_msg = dict()
dict_msg_parts = dict()

try:
    with open("ais_log1.txt", "a", encoding="utf-8") as txt_file_write, \
        open("ais_data.ndjson", "a", encoding="utf-8") as json_file_write:

        # while datetime.now() < deadline:
        while True:
            text = sock.recv(1024) # 括號內為字數值  256 / 8 = 32
            print(text)  # b'A,M,1,,,,,,,,,,,,,99.99,99.99,99.99*22\r\n'
            if not text:
                break
            # # 去除二進制寫入txt
            # ascii_msg = text.decode("ascii", errors="ignore")
            # print(ascii_msg)
            # print(ascii_msg.strip())
            # print(ascii_msg.replace('\r\n', ''))
            print(' ------------------------- ')
            txt_file_write.writelines(str(text))
            txt_file_write.flush()

            # ls_msg.append(ascii_msg.strip())

            # if ascii_msg.replace('\r\n', '').startswith('!AIVDM'):
            #     parts = ascii_msg.strip().split(',')
            #     total_parts = int(parts[1])  # 第二欄位是總部分數
            #     print(f'第二欄位是總部分數', total_parts)
            #     current_part = int(parts[2])  # 第三欄位是當前部分
            #     print(f'第三欄位是當前部分', current_part)
            #
            #     # 如果是第一部分或多部分訊息需要合併
            #     if total_parts > 1:
            #         if current_part == 1:
            #             buffer_msg = ascii_msg.strip()  # 開始拼接
            #             flag_VDM = True
            #         elif flag_VDM:
            #             buffer_msg += ascii_msg.strip()  # 繼續拼接
            #             if current_part == total_parts:
            #                 # 解析拼接完成的完整訊息
            #                 try:
            #                     decode_ais = pyais.decode(buffer_msg)
            #                     print(f'串接解碼後: {decode_ais}')
            #                     # 處理完成後，清空緩衝區
            #                     buffer_msg = ''
            #                     flag_VDM = False
            #                 except pyais.exceptions.UnknownMessageException as e:
            #                     print(f"無法解析的AIS訊息: {buffer_msg}")
            #                     buffer_msg = ''
            #                     flag_VDM = False
            #     else:
            #         # 單部分訊息，直接解析
            #         try:
            #             decode_ais = pyais.decode(ascii_msg)
            #             print(f'單部分解碼後: {decode_ais}')
            #         except pyais.exceptions.UnknownMessageException as e:
            #             print(f"無法解析的AIS訊息: {ascii_msg}")

            # if ascii_msg.strip().startswith("!AIVDM"):
            if ascii_msg.replace('\r\n', '').startswith('!AIVDM'):

                flag_VDM = True
                if '*' in ascii_msg:
                    decode_ais = pyais.decode(ascii_msg)
                    print(decode_ais)
                    flag_VDM = False
                else:
                    buffer_msg = ascii_msg.strip()

            else:
                if flag_VDM:
                    buffer_msg += ascii_msg.strip()
                    if '*' in ascii_msg:
                        decode_ais = pyais.decode(ascii_msg)
                        print(f'串接解碼後: {decode_ais}')
                        flag_VDM = False
                else:
                    buffer_msg = ''
                    continue

except KeyboardInterrupt:
    print("⚠️ 手動中止")

finally:
    sock.close()
    end_time = datetime.now()
    print("連線已關閉")
    print("===== Summary =====")
    print(f"Connect start : {connect_time}")
    # print(f"First AIS     : {first_ais_time if first_ais_time else 'N/A (no AIS received)'}")
    print(f"End time      : {end_time}")
    print(f"Run duration  : {end_time - connect_time}")
    # print(f"共接收 {total_chunks} 個 recv chunk，已寫入 {self.log_txt}")
    # print(f"AIS complete  : {ais_complete}, Output file   : {self.save_ndjson}")
