from geographiclib.geodesic import Geodesic

# 兩點座標（高雄案例示範）
lat1, lon1 = 22.63035, 120.29207   # 起點
lat2, lon2 = 22.614193, 120.284122   # 終點

g = Geodesic.WGS84.Inverse(lat1, lon1, lat2, lon2)

distance_km = g["s12"] / 1000.0

print("大地線距離: %.3f 公里" % distance_km)
# print("起點方位角: %.3f 度" % g["azi1"])
# print("終點方位角: %.3f 度" % g["azi2"])
