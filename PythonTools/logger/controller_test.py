"""
Run a test and record the output
"""
from util import get_input
from deepseaclient import DeepSeaClient
from analogclient import AnalogClient
import Adafruit_BBIO.PWM as PWM
from step_pwm import PWMInput
import time
import datetime
import logging
import os

dconfig = {'mode': "rtu",
           'dev': "/dev/ttyO1",
           'baudrate': 115200,
           'id': 10, # 8 for test deepsea, 10 for v2 deepsea
           'mlistfile': "cur_rpm.csv",
           }

aconfig = {
        'measurements': {'voltage': "P9_39", 'current': "P9_40"},
        'frequency': 0.1
        }

rpm_sig = "P9_22"
ww_sig = "P9_21"
rpm_default = 0

# Get a logger and logging handler
logger = logging.getLogger(__name__)
lh = logging.NullHandler()
logger.addHandler(lh)

# get deepsea thread
deepsea = DeepSeaClient(dconfig, lh)

# Get stepping pwm thread
input_thread = PWMInput(ww_sig)

# Get analog input thread
analog = AnalogClient(aconfig)

PWM.start(rpm_sig, rpm_default, 100000)

log_dir = "../../Data Analysis/test_logs/"
now = datetime.datetime.now()
today = now.strftime("%Y-%m-%d")
i=0
while os.path.exists(log_dir + today + "_run%d.csv"%i):
    i += 1

logfile_name = log_dir + today + "_run%d.csv" % i

with open(logfile_name, mode="w") as f:
    print("Opened file")
    input_thread.start()
    print("Started input thread")
    deepsea.start()
    print("Started deepsea")
    analog.start()
    print("Started analog")
    s = "%s,%s,%s,%s,%s,%s,%s,%s,%s\n"%("time", "rpm", "ds_volt",
                          "ds_cur_300v", "ds_cur_48v", "soc", "ds_bat_cur",
                          "an_cur_300v", "an_volt")
    f.write(s)
    print(s)

    raw_input("Press enter to start logging data")
    try:
        i = 0
        while True:
            # Read in values from deepsea
            values = deepsea.values
            t = values["Sample Time"]
            volts = values['300V Bus Volt']
            ds_amps = values['300V Charge Amp']
            rpm = values['Engine Speed']

            # read in analog values
            an_amps = analog.values['current']
            an_volts = analog.values['voltage']

            # Output RPM on PWM
            rpm_val = rpm_default
            if 2100 <= rpm <= 3000:
                rpm_val = (rpm - 2100) / 900 * 100 # Scale between 0 and 100
            PWM.set_duty_cycle(rpm_sig, rpm_val)

            # Log the data for this timestamp
            s = deepsea.csv_line() + analog.csv_line() + '\n'
            f.write(s)

            if i == 10:
                i = 0
                deepsea.print_data()
                print("%20s %10.2f %10s"%("High Bus V raw", an_volts, "V"))
                print("%20s %10.2f %10s"%("Generator cur raw", an_amps, "V"))
                print("-"*80)

            # Sleep 1/10 second
            time.sleep(0.1)

            i += 1

    except KeyboardInterrupt:
        deepsea.cancel()
        deepsea.join()

        analog.cancel()
        analog.join()

        input_thread.cancel()
        input_thread.join()
        exit()

