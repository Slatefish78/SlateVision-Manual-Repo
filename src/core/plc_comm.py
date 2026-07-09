import logging

from pycomm3 import LogixDriver

logger = logging.getLogger(__name__)

class PlcComm():

    PLC_INPUT_TAGS = {"total_status","running"}
    PLC_OUTPUT_TAGS = {"trigger"}

    def __init__(self,ip,tag):
        self.ip = ip
        self.tag = tag
        self.plc = LogixDriver(ip)

        logger.debug(f"Created {self}.")

    def __repr__(self):
        return f"{self.__class__.__name__}"

    def read(self,tag):
        return self.plc.read(tag).value
        
    def write(self,tag,value):
        self.plc.write(tag,value)

    def write_udt(self, total_status:bool, is_running:bool):
        self.write(self.tag + ".total_status",total_status)
        self.write(self.tag + ".running",is_running)

    def clear_udt(self):
        self.write(self.tag + ".total_status",False)
        self.write(self.tag + ".running",False)

    def open_connection(self,retry=False,attempted=0):
        logger.debug(f"Opening PLC connection.")

        self.plc.open()
        # except Exception as e:
        #     logger.debug(f"PLC failed to open: {str(e)}")
        #     if retry:
        #         time.sleep(5)
        #         logger.debug(f"Retrying... ({attempted + 1})")
        #         self.open_connection(retry=True, attempted=attempted+1)
        #     else:
        #         raise
        
        if self.plc.connected:
            logger.debug(f"Opened PLC connection.")
        return self.plc.connected

    def close_connection(self):
        logger.debug(f"Closing PLC connection.")
        self.plc.close()
        logger.debug(f"Closed PLC connection.")