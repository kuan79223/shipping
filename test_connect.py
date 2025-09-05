import socket
import json
from datetime import datetime, timedelta


def run_socket_reader(
        host="192.168.2.1",  # 預設目標主機 IP
        port=3333,  # 預設目標端口
        out_ndjson="ais_data.ndjson",  # 預設輸出 NDJSON 檔案
        out_raw="ais_raw_log.txt",  # 預設輸出原始日誌檔案
        run_minutes=60,  # 預設運行時間（分鐘）
        recv_bufsize=4096  # 預設接收緩衝區大小
):
    # 建立 socket 連線
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((host, port))  # 嘗試連接到指定主機和端口
        print(f"Connected to {host}:{port}")
    except Exception as e:
        print(f"Error connecting to {host}:{port} - {e}")
        return

    # 關閉 socket 連線
    sock.close()


# 呼叫函式來測試連線並接收資料
run_socket_reader()
