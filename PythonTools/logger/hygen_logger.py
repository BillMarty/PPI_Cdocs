{
    'deepsea': {
        'mlistfile': 'cur_rpm.csv',
        'baudrate': 115200,
        'mode': 'rtu',
        'dev': '/dev/ttyO1',
        'id': 10
    },
    'woodward': {'ww_sig': 'P9_21'},
    'enabled': ['deepsea', 'bms', 'woodward', 'analog', 'filewriter'],
    'bms': {
        'baudrate': 9600,
        'sfilename': '/home/hygen/log/bmsstream.log',
        'dev': '/dev/ttyO4'
    },
    'filewriter': {
        'ldir': '/home/hygen/dev/PPI_Cdocs/data_analysis/test_logs'
    },
    'analog': {
        'averages': 8,
        'measurements': [
            ['an_300v_cur', 'A', 'P9_40', 40.0, -0.2],
            ['an_300v_volt', 'V', 'P9_39', 1.0, 0.0]
            ],
        'frequency': 1.0
    },
    'logfile': 'errors.log',
}
