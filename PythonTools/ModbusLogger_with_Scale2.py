# try pyModbusTCP

from pyModbusTCP.client import ModbusClient
import time
import serial

USESCALES = False  # assume the scales will not be used
weight=[0,0,0,0,0,0,0]  #keep track of previous fule scale weights
max31=2**31
max32=2**32
## meas = ["name","units",addr,len,gain,offset]
MLname=0
MLunits=1
MLaddr=2
MLlen=3
MLgain=4
MLoff=5
# MeasList=[["Oil P","psi",1024,1,1.0,0.0],
#           ["Eng T","degC",1025,1,1.0,0.0],
#           ["E-Bat","V",1029,1,0.1,0.0],
#           ["Run T","min",1798,2,0.016667,0.0],
#           ["Starts","",1808,2,1.0,0.0],
#           ["SOC","%",43809,1,1.0,0.0],
#           ["+/-Bat","A",43811,1,0.5,50],
#           ["EGT","degC",43978,1,1.0,0.0],
#           ["Bat T","degC",43981,1,1.0,0.0]]
logDisp=""

#get and scan the measurement description file
MdfDef="V1.csv"
MDF=input("Measurement description file (%s): "%(MdfDef))
if MDF=="":
    MDF=MdfDef
    
mdf=open(MDF)
MList=mdf.readlines()
MeasList=[]
labels=""
for (n,line) in enumerate(MList):
    #print(n,line)
    rline=line.split(',')
    #print(rline)
    if n>=2:
        MeasList.append([rline[0],rline[1],int(rline[2]),int(rline[3]),float(rline[4]),float(rline[5])])
        #print(MeasList)
        labels = labels+format("%s,"%rline[0])

print(labels)
#print(MeasList)

c=ModbusClient

# init serial port for reading scale
yn = input("Use scales? (y/n) ")
if yn=='Y' or yn=='y':
    com = input("Com port? (com2) ")
    if com == "":
        com="com2"
    ser = serial.Serial(port=com,baudrate=9600)
    ser.timeout = 0.5
    USESCALES=True

# enter IP address and port number
inHostDef="10.50.0.210"
inHOST=input("Host Addr (%s)? "%(inHostDef))
if inHOST=="":
    inHOST=inHostDef

inPortDef="1003"
inPORT=input("Port # (%s)? "%(inPortDef))
if inPORT=="":
    inPORT=inPortDef
inPORT=int(inPORT)           
try:
    c = ModbusClient(host=inHOST, port=inPORT)
except ValueError:
    print("Error with host or port params")

logDef="Test.csv"
logfile=input("CSV Logfile name (%s) "%(logDef))
if logfile=="":
    logfile=logDef
lf=open(logfile,mode='w')

comDef="No Comment"
comment=input("Enter a Comment/Description line: ")
if comment=="":
    comment=comDef
    
lf.write(comment+"\n")
lf.write(labels+"\n")

try:
    # get and display some Modbus data
    while True:
        if c.is_open():
            if USESCALES:
                ser.write(b'~*P*~') # send poll command to scale
            logDisp=""
            for meas in MeasList:
                try:
                    reg1 = c.read_holding_registers(meas[MLaddr],meas[MLlen])
                    if type(reg1)=='NoneType':
                        x = -9999.9     # special place holder / flag for missed MODBUS data
                    else:
                        #print(reg1)
                        if meas[MLlen]==2:
                            reg1[0]=reg1[1] + 65536.0*reg1[0]
                            if reg1[0]>max31:
                                reg1[0]=reg1[0]-max32-1
                        #print(reg1[0])
                        x=float(reg1[0])*meas[MLgain]+meas[MLoff]
                except TypeError as e:  # flag error for debug purposes
                    print("reg1=",reg1)
                    print("meas=",meas)
                    print(e)
                    lf.write("-- TypeError Occured --\r\n\n")
                    x=-9999.8

                measDisp = "%20s %10.2f %10s"%(meas[MLname],x,meas[MLunits])
                print(measDisp)
                logDisp=logDisp+format("%8.6f,"%x) #need 6 digits for time to dislay seconds
        else:
            print("Reopen")
            c.open()
            
        time.sleep(1)
        if USESCALES:
            scale = ser.readlines()
            #print(scale)
            scale=str(scale)
            scale=scale.split(' ') #append the scale weight date,time,weight,eol
            #print(scale)
            scale=scale[0][3:]
            #print(scale)
            if len(scale)>1:
                logDisp = logDisp + scale
                print("scale=%s"%scale)
                weight=weight[1:]
                weight.append(float(scale))
                print(weight)
                print("Fuel delta (lit/min): %10.3f"%((weight[0]-weight[6])/85))

        if len(logDisp)>0:
            lf.write(logDisp+"\n")
        print("")

finally:
    c.close()
    lf.close()
