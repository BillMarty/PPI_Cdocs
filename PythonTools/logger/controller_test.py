from util import get_input
from deepseaclient import DeepSeaClient
import Adafruit_BBIO.PWM as PWM
from step_pwm import PWMInput
import time
import logging

dconfig = {'mode': "rtu",
           'dev': "/dev/ttyO1",
           'baudrate': 115200,
           'id': 10,
           'mlistfile': "cur_rpm.csv",
           }

logger = logging.getLogger(__name__)
deepsea = DeepSeaClient(dconfig, logger)

ww_sig = "P9_21"
input_thread = PWMInput(ww_sig)

rpm_sig = "P9_22"
PWM.start(rpm_sig, 50, 100000)

logfile_name = get_input("Enter a name for the log file:", default="data.csv")
with open(logfile_name, mode="w") as f:
    deepsea.run()
    input_thread.run()
    f.write("%s,%s,%s,%s"%("Time", "300V Bus Volt", "300V Charge Amp", "RPM"))
    try:
        while True:
            # Read in values
            values = deepsea.values
            volts = values['300V Bus Volt']
            amps = values['300V Charge Amp']
            rpm = values['Engine Speed']

            # Output RPM on PWM
            rpm_val = (rpm - 2100) / 900 * 100 # Scale between 0 and 100
            PWM.set_duty_cycle(rpm_sig, rpm_val)

            # Log the data for this timestamp
            s = "%d,%f,%f,%f\n"%(volts, amps, rpm)
            print(s)
            f.write(s)

            # Sleep 1/10 second
            time.sleep(0.1)

    except KeyboardInterrupt:
        deepsea.cancel()
        deepsea.join()
        input_thread.cancel()
        input_thread.join()
        exit()

