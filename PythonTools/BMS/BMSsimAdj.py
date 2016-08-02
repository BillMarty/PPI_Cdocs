#emulate the Beckett BSM data stream
import serial
import time
import cv2

soc_scale = 100
soc_value = 50

def set_scale(val):
    global soc_value
    soc_value = val

fname="bms2.log"
ser = serial.Serial('COM14',9600)
cv2.namedWindow('SOC', 0)
cv2.createTrackbar('scale', 'SOC', soc_value, soc_scale, set_scale)

for buf in open(fname):
    rec=buf[9:]
    if rec[4] == 'S':
        soc = ('%3.3d'%(soc_value))
        rec2=rec[0:19]+soc+rec[22:]
        rec=rec2
    print rec
    ser.write(rec)
    time.sleep(1)
    cv2.waitKey(10)

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