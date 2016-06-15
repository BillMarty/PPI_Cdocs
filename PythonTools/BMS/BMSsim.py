#emulate the Beckett BSM data stream
import serial
import time

fname="bms2.log"
ser = serial.Serial('COM14',9600)

for buf in open(fname):
    rec=buf[9:]
    print rec,
    ser.write(rec)
    time.sleep(1)

    # sum1=0
    # sum2=0
    # for n in rec:
    #     sum1 += ord(n)
    #     if sum1 >= 255:
    #         sum1 -= 255
    #     sum2 += sum1
    #     if sum2 >= 255:
    #         sum2 -= 255
    #    print('%c  %2.2x  %2.2x  %2.2x'%(n,ord(n),sum1,sum2))