import pyais



str_123 = 'asga5ha6d1h35'



print(str_123[:6])
if str_123[-3] == 'h':
    print(str_123[-3])

a = b'Hello\r\n'
b = b'world\r\n'

# 合併後在解碼
combined_bytes = a + b
combined_str = combined_bytes.decode('ascii')
print(combined_str)

# 解碼後再合併
ascii_a = a.decode('ascii')
ascii_b = b.decode('ascii')
print(ascii_a + ascii_b)
# 以上兩者輸出相同

# 需要將\r\n 換成空白   二進制相加解碼再取代
combined_str = (a + b).decode('ascii').replace('\r\n', '')
print(combined_str)

text = b'!AIVDM,1,1,,A,17VL1>?P018VSt<<t8TFvgw80L6b,0*3A'

decode_ais = pyais.decode(text)
# print(decode_ais)


list1 = ['AIVDM', '2', '1', 'xxxxxxxxx']
print(int(list1[2]))

list2 = ['AIVDM', '2', '2', '0000']

dict1 = dict()
dict1[0] = []
dict1[0].append(list1[3])
dict1[0].append(list2[3])
print(dict1)


result = ''.join(dict1[0])
print(result)

# result = ''.join(dict1[k] for k in sorted(dict1.keys()))
# print(result)
