import os
import json
import socket
from datetime import datetime, timedelta

import pandas as pd
import pyais

# ============== 基本常數 ==============
AIS_STARTS = ("!AIVDM", "!AIVDO")

# ============== 工具：chunk -> 行 ==============
def bytes_stream_to_lines(byte_chunks):
    """
    把 socket 逐次 recv 的 bytes 串流，切成「行」：
    - 支援 \r\n / \n / \r
    - 尾端殘段會帶到下一個 chunk 補齊
    """
    carry = ""
    for chunk in byte_chunks:
        text = chunk.decode("ascii", errors="ignore")
        text = text.replace("\r", "\n")
        parts = (carry + text).split("\n")
        *full, carry = parts
        for line in full:
            if line:
                yield line
    if carry:
        yield carry  # 可能是不完整行，交給上層處理/丟棄

# ============== 檢查與解析 NMEA/AIS ==============
def has_valid_tail_checksum(nmea_line: str) -> bool:
    if "*" not in nmea_line:
        return False
    star = nmea_line.rfind("*")
    # 必須剛好 *HH
    if len(nmea_line) - star - 1 != 2:
        return False
    hh = nmea_line[star+1:]
    return all(c in "0123456789abcdefABCDEF" for c in hh)

def checksum_ok(nmea_line: str) -> bool:
    try:
        body, hh = nmea_line.strip().split("*")
        calc = 0
        for ch in body[1:]:  # 跳過開頭的 ! 或 $
            calc ^= ord(ch)
        return calc == int(hh, 16)
    except Exception:
        return False

def parse_header_fields(nmea_line: str):
    """
    解析 !AIVDM 標頭：
    !AIVDM,frag_total,frag_num,seq_id,channel,payload,fill*CS
    回傳 (frag_total:int, frag_num:int, seq_id:str, channel:str)
    """
    core, _ = nmea_line.split("*", 1)
    parts = core.split(",")
    if len(parts) < 7:
        raise ValueError("invalid AIVDM parts")
    return int(parts[1]), int(parts[2]), parts[3], parts[4]

# ============== 分段重組：yield list[str] ==============
def iter_grouped_aivdm(lines_iterable, expire_seconds=5):
    """
    依 seq_id + channel 重組多段 AIVDM。
    輸出：每次 yield 一個 list[str]（單段=1行，多段=N行）。
    """
    from datetime import datetime, timedelta
    buckets = {}  # key -> {'total':N,'frags':{idx:line},'ts':datetime}

    def make_key(seq_id, channel):
        # 規範上多段會帶 seq_id；若空，就退化用 channel（風險較高，但可用過期機制保護）
        return (seq_id if seq_id else f"__empty__{channel}", channel)

    for raw in lines_iterable:
        line = raw.strip()
        if not line or not line.startswith(AIS_STARTS):
            continue
        if not has_valid_tail_checksum(line) or not checksum_ok(line):
            # Checksum 錯誤，丟掉
            continue

        try:
            total, num, seq, ch = parse_header_fields(line)
        except Exception:
            continue

        if total == 1:
            # 單段：直接輸出（包成 list 以統一型別）
            yield [line]
            continue

        # 多段：放進桶子
        key = make_key(seq, ch)
        now = datetime.utcnow()
        b = buckets.get(key)
        if b is None or (now - b['ts']) > timedelta(seconds=expire_seconds):
            b = {'total': total, 'frags': {}, 'ts': now}
            buckets[key] = b

        b['frags'][num] = line
        b['ts'] = now

        # 集滿 -> 依序輸出
        if len(b['frags']) == b['total']:
            parts = [b['frags'][i] for i in range(1, b['total'] + 1)]
            yield parts
            del buckets[key]

# ============== 將 pyais 訊息轉字典（可加時間戳） ==============
def ais_to_dict(ais_msg, recv_time: datetime):
    """
    將 pyais decode 出來的訊息轉為可寫入 NDJSON 的 dict。
    這裡把接收時間也一起寫入。
    """
    try:
        d = ais_msg.asdict()
    except Exception:
        # 老版本接口
        d = json.loads(ais_msg.to_json())
    d["_recv_time"] = recv_time.isoformat()
    return d

# ============== 主流程：讀取 socket -> RAW/NDJSON/Excel ==============
def run_socket_reader(
    host="192.168.2.1",
    port=3333,
    out_ndjson="ais_data.ndjson",
    out_raw="ais_raw_log.txt",
    run_minutes=60,
    recv_bufsize=4096
):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    connect_time = datetime.now()
    deadline = connect_time + timedelta(minutes=run_minutes)

    first_ais_time = None
    ais_complete = 0
    total_chunks = 0

    print(f"{connect_time} Start...")

    try:
        with open(out_ndjson, "a", encoding="utf-8") as json_file_write, \
             open(out_raw, "a", encoding="utf-8") as raw_file_write:

            # ---- 逐次從 socket 拉 bytes ----
            def chunk_iter():
                nonlocal total_chunks
                while True:
                    if datetime.now() >= deadline:
                        break
                    data = sock.recv(recv_bufsize)
                    if not data:
                        break

                    # 原樣寫 raw 檔（保持原始換行；若最後無換行，就補一個）
                    text = data.decode("ascii", errors="ignore")
                    if not text.endswith("\n"):
                        text += "\n"
                    raw_file_write.write(text)
                    raw_file_write.flush()

                    total_chunks += 1
                    yield data

            line_iter = bytes_stream_to_lines(chunk_iter())

            # 依序取得「已重組完成」的 AIVDM parts（list[str]）
            for parts in iter_grouped_aivdm(line_iter):
                try:
                    # 單段或多段都可這樣解
                    ais_msg = pyais.decode(*parts)

                    if first_ais_time is None:
                        first_ais_time = datetime.now()

                    now_time = datetime.now()
                    dict_ais_msg = ais_to_dict(ais_msg, recv_time=now_time)

                    json_file_write.write(json.dumps(dict_ais_msg, ensure_ascii=False) + "\n")
                    json_file_write.flush()
                    ais_complete += 1

                except Exception:
                    # 解析失敗可在此記錄 parts 做除錯
                    # print("Decode fail:", e, parts)
                    pass

    except KeyboardInterrupt:
        print("⚠️ 手動中止")
    finally:
        sock.close()
        end_time = datetime.now()
        print("連線已關閉")
        # ===== Summary =====
        print(f"Connect start : {connect_time}")
        print(f"First AIS     : {first_ais_time if first_ais_time else 'N/A (no AIS received)'}")
        print(f"End time      : {end_time}")
        print(f"Run duration  : {end_time - connect_time}")
        print(f"recv() chunks : {total_chunks} written to {out_raw}")
        print(f"AIS complete  : {ais_complete}, NDJSON : {out_ndjson}")

        # ---- 將 NDJSON 轉 Excel（若有資料） ----
        try:
            if os.path.exists(out_ndjson) and os.path.getsize(out_ndjson) > 0:
                df = pd.read_json(out_ndjson, lines=True)
                base, _ = os.path.splitext(out_ndjson)
                df.to_excel(f"{base}.xlsx", index=False)
                print("已將 NDJSON 轉換為 Excel")
            else:
                print("NDJSON 是空的，略過讀取/轉換。")
        except ValueError as e:
            print(f"讀取 NDJSON 失敗：{e}。請檢查檔案內容是否每行皆為有效 JSON。")

# ============== 範例啟動（可依需求修改） ==============
if __name__ == "__main__":
    # 依你的環境調整 host/port/檔名/時間
    run_socket_reader(
        host="192.168.2.1",
        port=3333,
        out_ndjson="ais_data.ndjson",
        out_raw="ais_raw_log.txt",
        run_minutes=5,        # 跑 60 分鐘；要短測就改 1
        recv_bufsize=4096      # 4096/8192 都行；正確性與這個值無關
    )
