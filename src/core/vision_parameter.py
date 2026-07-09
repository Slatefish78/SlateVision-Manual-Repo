import logging

from core.vision_tool import VisionTool

logger = logging.getLogger(__name__)

class VisionParameter():

    MEASUREMENT_VALUES = ["score","class","x","y","area","count"]
    LOGICAL_VALUES = ["and","or","not"]

    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value
        
        self.latest_pass = False

        self.tool_input = None
        self.param_inputs = []
        self.thresh_low = None
        self.thresh_high = None

        if self.value not in self.MEASUREMENT_VALUES and self.value not in self.LOGICAL_VALUES:
            raise ValueError(f"Invalid parameter value: {self.value}")

        logger.debug(f"Created {self}.")

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name},value={self.value})"

    def is_measurement(self):
        return self.value in self.MEASUREMENT_VALUES
    
    def is_logical(self):
        return self.value in self.LOGICAL_VALUES
    
    def set_measurement_attributes(self,tool_input: VisionTool,thresh_low: float,thresh_high: float):
        logger.debug(f"Setting {self} measurement attributes.")
        if not self.is_measurement():
            raise ValueError("Parameter value is not a measurement type")
        
        self.tool_input = tool_input
        self.param_inputs = []
        self.thresh_low = thresh_low
        self.thresh_high = thresh_high

        logger.debug(f"Set {self} measurement attributes: (tool_input={self.tool_input},thresh_low={self.thresh_low},thresh_high={thresh_high}).")

    def set_logical_attributes(self,param_inputs: list["VisionParameter"]):
        logger.debug(f"Setting {self} logical attributes.")
        if not self.is_logical():
            raise ValueError("Parameter value is not a logical type")
        
        self.tool_input = None
        self.param_inputs = param_inputs
        self.thresh_low = None
        self.thresh_high = None

        logger.debug(f"Set {self} logical attributes: (param_inputs={self.param_inputs}).")

    def compute_passes(self):
        # measurement parameters: check if value is between thresholds
        if self.is_measurement():
            results = self.tool_input.get_results()
            if not results:
                self.latest_pass = False
                return self.latest_pass
            
            best = results[0]

            match self.value:
                case "score":
                    criterion = best["score"]
                case "class":
                    criterion = best["class_id"]
                case "x":
                    # x center = average
                    criterion = (best["x1"] + best["x2"])/2
                case "y":
                    # y center = average
                    criterion = (best["y1"] + best["y2"])/2
                case "area":
                    # area = width * height
                    criterion = abs(best["x2"] - best["x1"]) * abs(best["y2"] - best["y1"])
                case "count":
                    criterion = len(results)
                case _:
                    self.latest_pass = False
                    return
            
            self.latest_pass = self.thresh_low <= criterion <= self.thresh_high
        
        # logical parameters: check pass condition of parameter inputs
        elif self.is_logical():
            pass_list = [p.passes() for p in self.param_inputs]
            match self.value:
                case "and":
                    self.latest_pass = all(pass_list)
                case "or":
                    self.latest_pass = any(pass_list)
                case "not":
                    self.latest_pass = all(not p for p in pass_list)
                case _:
                    self.latest_pass = False
                    return

    def passes(self):   
        return self.latest_pass
    
    def export_dict(self):
        return_dict = {
            "name": self.name,
            "value": self.value,
            "inputs": [] # overwritten by vision project export
        }

        if self.thresh_low is not None:
            return_dict["thresh_low"] = self.thresh_low
        if self.thresh_high is not None:
            return_dict["thresh_high"] = self.thresh_high

        return return_dict