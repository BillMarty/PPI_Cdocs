import timeit

setup = '''
from pymodbus.client.sync import ModbusSerialClient
client = ModbusSerialClient(method='rtu', port='/dev/ttyUSB0', baudrate=9600)
client.connect()
'''

statement = '''
r = client.read_holding_registers(1025, 1, unit=0x08)
if r == None: print("error")
else: print("ok")
'''

# There are 19 values currently being pulled out of DeepSea
t = timeit.timeit(stmt=statement, setup=setup, number=19)
print("To pull 19 values (16-bit) from DeepSea takes " + str(t) + " seconds")

