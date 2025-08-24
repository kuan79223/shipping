import pandas as pd

# 讀取 NDJSON 文件
ndjson_file = 'ais_data_24V_0850_desk.ndjson'  # 假設你的 NDJSON 文件名為 ais_data_12V_part1.ndjson
df = pd.read_json(ndjson_file, lines=True)

# 將資料保存為 Excel 格式
df.to_excel('ais_data_24V_0850_desk.xlsx', index=False)

print("已將 NDJSON 轉換為 Excel")
