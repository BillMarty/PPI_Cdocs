# analogclient.py

- ADC.setup throws RuntimeError on ADC error - handled in main.py
- config file does not have required config values throws ValueError - handled in main.py
- averages is set to 0 in the config file, causing div by 0 - handled in `AnalogClient.__init__`, throws ValueError, handled in main.py
- time is corrected backwards, so we never report a value (time not monotonic) - handled by using the `monotonic` library
- ADC.read_raw returns RuntimeError, ValueError, or IOError
- Measurement with invalid IO Pins or lists

# bmsclient.py

- Error opening serial port
- Stream file unable to open for appends
- Constructor fails: caller must handle
- Integer conversion of charge or SoC fails (Extremely unlikely - we have confirmed checksum) But try blocks are cheap
- Integer conversion of checksum fails (ValueError)
- Stream file write error (USB removed, corrupted, unmounted, etc.)

# config.py

- Not important. Once we're in production, this will just read in a configuration file once at the beginning.

# deepseaclient.py

- Constructor fails
	+ Cannot open serial port
	+ Fails out of constructor before `_client` assigned, so `__del__` throws an exception
	+ Read measurement description file fails
- Time set during loop (non-monotonic)
- Modbus execute errors
	+ Sending errors
		* SerialException from serial.serialutil
		* portNotOpenError from serial.serialutil
		* writeTimeoutError from serial.serialutil
	+ Receiving errors:
		* SerialException from serial.serialutil
		* portNotOpenError from serial.serialutil
	+ Modbus errors:
		* ModbusError from modbus_tk.exceptions
		* ModbusInvalidResponseError from modbus_tk.exceptions
- Getting out of sync in modbus_tk?

# entry.py

- Not terribly important, since it only runs once
- Changed file locations problematic for hardcoded log, directory, config file

# logfilewriter.py

- 'ldir' key not in config
- constructor errors
- Main thread crashes, how do we respond?
- File cannot be written to (full disk, USB removed, etc.)

# main.py

- Threads crash - monitor and restart
- print_data raises an exception from one of the clients
- csv_line raises an exception from one of the clients
- Queue runs out of space (unlikely, since we're using an unlimited queue. Only if logfilewriter crashes)
- analog.values does not have the necessary key 'current' for sending to woodwardcontrol as process_variable
- Unhandled exceptions ought to restart the program

# woodwardcontrol.py

- Constructor exceptions
	+ ValueError for invalid config map
	+ ValueError for invalid config value such as PWM pin
- Still need to debug compute and main run loop
