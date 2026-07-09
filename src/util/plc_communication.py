from pycomm3 import LogixDriver, SLCDriver


def connect_driver(ip:str) -> LogixDriver|SLCDriver|None:
    for Driver in (LogixDriver, SLCDriver):
        try:
            plc = Driver(ip)
            if plc.open() and plc.connected:
                plc.close()
                print(f"Connected to PLC: {type(plc)}({ip})")
                return plc
        except:
            pass

    return None