import math

# 哈弗辛公式 - arcsin 版本
def haversine_arcsin(lon1, lat1, lon2, lat2):
    R = 6371.0  # 地球半徑 (km)
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))   # 用 arcsin
    return R * c

# 哈弗辛公式 - atan2 版本（數值更穩定）
def haversine_atan2(lon1, lat1, lon2, lat2):
    R = 6371.0  # 地球半徑 (km)
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))  # 用 atan2
    return R * c

# 測試兩種方法
lon1, lat1 = 121.5, 25.0   # 台北
lon2, lat2 = 139.7, 35.7   # 東京

d1 = haversine_arcsin(lon1, lat1, lon2, lat2)
d2 = haversine_atan2(lon1, lat1, lon2, lat2)

print("Arcsin 版本距離:", d1, "km")
print("Atan2 版本距離:", d2, "km")
