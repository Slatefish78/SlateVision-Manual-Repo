import logging
from pathlib import Path
import threading
import time

from pycomm3 import LogixDriver, SLCDriver

from core.camera import Camera
from core.sv_project import SVProject
from core.vision_tool import DetectTool
from core.vision_parameter import VisionParameter
from util.plc_communication import connect_driver

logger = logging.getLogger(__name__)

class VisionProject(SVProject):
    """
    Base class for a runnable Vision Project

    Args:
        config_file_path: path to .json config file which holds the data for this project.

    Methods:
        start_operation(): Activate all cameras, start a background thread, loop through all tools and parameters and evaluate success.
        stop_operation(): Stop running thread, deactivate cameras, clear all data.
        export_dict(): Returns Vision project data in dict format (ready for json dump).
        save_config(): Export project data as project_config.json at project_folder_path.
    """

    PLC_SIGNAL_TYPES = ["Running Indicator","Trigger Bit","Output Bit"]

    #region Init
    def __init__(self,config_file_path: Path):
        super().__init__(config_file_path)
        
        self.model_path = self.project_folder_path / "models"
        self.model_path.mkdir(parents=True,exist_ok=True)

        self.plc_ip = self.project_config.get("project","plc_ip")
        self.plc = None
        self.plc_map = self.project_config.get("plc_map",default=[])
        self.loop_interval = self.project_config.get("project","loop_interval")
        self.is_triggered = self.project_config.get("project","triggered")

        self.cameras = []
        self.tools = []
        self.parameters = []

        # stored frames for GUI display
        self.opening_camera_index = None
        self.frames = []

        # create camera objects
        for camera in self.project_config.get("cameras"):
            new_cam = Camera.from_dict(camera)
            self.cameras.append(new_cam)

        # create vision tool objects
        for tool in self.project_config.get("tools"):
            camera = self.cameras[tool["camera"]]
            match tool["tool_type"]:
                case "detect":
                    self.tools.append(DetectTool(tool["name"],camera,tool["render"], self.model_path / tool["model"]))
                case _:
                    raise ValueError(f"Invalid tool tool_type: {tool['tool_type']}")

        for parameter in self.project_config.get("parameters"):
            new_param = VisionParameter(parameter["name"],parameter["value"])
            if new_param.is_measurement():
                new_param.set_measurement_attributes(
                    tool_input=self.tools[parameter["inputs"][0]],
                    thresh_low=parameter["thresh_low"],
                    thresh_high=parameter["thresh_high"]
                )
            elif new_param.is_logical():
                new_param.set_logical_attributes(
                    param_inputs=[self.parameters[i] for i in parameter["inputs"]],
                )

            self.parameters.append(new_param)

        # running and thread data
        self.is_running = False
        self.using_plc = True
        self._thread = None
        self._lock = threading.Lock()

        logger.debug(f"Created {self}.")
    
    def __repr__(self):
        return f"{self.__class__.__name__}(cameras={self.cameras}\ntools={self.tools}\nparameters={self.parameters})"
    
    #region Start Operation
    def start_operation(self):
        logger.info(f"Starting project {self.project_name} operation.")
        
        # skip if already active
        if self.is_running:
            logger.info(f"Project is already running.")
            return

        # start background thread
        self.is_running = True
        self._thread = threading.Thread(
            target=self.operation_loop,
            daemon=True
        )
        self._thread.start()
        
        logger.info(f"Started project {self.project_name} operation.")

    #region Operation Loop
    def operation_loop(self):
        prev_trigger_vals = [False] * 100

        # connect to plc
        self.plc = connect_driver(self.plc_ip)
        if self.plc:
            logger.debug(f"Connected to PLC: {type(self.plc)}({self.plc_ip})")
            self.using_plc = True
        else:
            print("Running without PLC")
            logger.debug(f"Failed to connect to PLC. Running without PLC communication.")
            self.using_plc = False

        if self.plc:
            self.plc.open()

        while self.is_running:
            try:
                # initialize loop timer
                loop_start = time.time()

                # activate cameras
                for i, camera in enumerate(self.cameras):
                    if not camera.is_running or (camera.latest_frame is not None and camera.latest_frame_time is not None and (time.time() - camera.latest_frame_time) > 5):
                        try:
                            self.opening_camera_index = i+1
                            camera.start_connection()
                        finally:
                            self.opening_camera_index = None            

                # signal running to plc
                if self.using_plc:
                    for signal in self.plc_map:
                        if signal["type"] == "Running Indicator":
                            self.plc.write((signal["tag"],True))

                # read trigger value from plc
                cur_trigger_vals = []
                if self.is_triggered and self.using_plc:
                    for signal in self.plc_map:
                        if signal["type"] == "Trigger Bit":
                            cur_value = self.plc.read(signal["tag"]).value
                            cur_trigger_vals.append(cur_value)

                # run operation based on triggered project and trigger value
                if (not self.is_triggered or 
                    (self.is_triggered and any(
                        cur and not prev
                        for cur, prev in zip(cur_trigger_vals,prev_trigger_vals)
                    ))
                ):
                        
                    # execute operation for vision tools
                    for tool in self.tools:
                        tool.predict_results()

                    # execute operation for vision parameters
                    for param in self.parameters:
                        param.compute_passes()
                        
                    # read/store vision parameters
                    if self.using_plc:                     
                        # bit outputs
                        for signal in self.plc_map:
                            if signal["type"] == "Output Bit":
                                self.plc.write((signal["tag"],self.parameters[signal["value"]].passes()))

                    # update displayed camera frames
                    self.frames = []
                    for camera in self.cameras:
                        self.frames.append(camera.get_last_frame())

                # wait times based on whether project is trigger-based
                if self.is_triggered:
                    time.sleep(0.005)
                else:
                    time.sleep(max(0,self.loop_interval - (time.time() - loop_start)))

                # end-of-loop cleanup
                prev_trigger_vals = cur_trigger_vals
        
            except:
                logger.exception("Vision Project nonfatal loop error. Continuing in 1s.")
                time.sleep(1)

    #region Stop Operation
    def stop_operation(self):
        """Stop background thread, deactivate all cameras"""
        logger.info(f"Stopping project {self.project_name} operation.")
        if not self.is_running:
            logger.info("Project is not running.")
            return
        
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        self.stop_cameras()

        # clear frame/tool data
        self.frames = []
        for tool in self.tools:
            tool.latest_results = []

        # clear plc tags
        if self.using_plc:
            for signal in self.plc_map:
                if signal["type"] == "Running Indicator" or signal["type"] == "Output Bit":
                    self.plc.write((signal["tag"],False))

        if self.plc:
            self.plc.close()

        logger.info(f"Stopped project {self.project_name} operation.")

    #region Misc Methods
    def start_cam(self,index):
        def worker():
            self.opening_camera_index = index + 1
            self.cameras[index].start_connection()
        
            self.opening_camera_index = None

        threading.Thread(target=worker,daemon=True).start()

    def stop_cameras(self):
        for camera in self.cameras:
            camera.end_connection()

    def export_dict(self):
        """Returns (dict): Vision project data in dict format (ready for json dump)."""
        # merge project export with vision project specific data
        export_dict = {
            "project": {
                **super().export_dict().get("project",{}),
                "plc_ip": self.plc_ip,
                "loop_interval": self.loop_interval,
                "triggered": self.is_triggered
            },
            "cameras": [],
            "tools": [],
            "parameters": [],
            "output_map": {}
        }
        # output camera list
        for camera in self.cameras:
            export_dict["cameras"].append(camera.export_dict())
        # output tool list, record camera index of tool
        camera_index_map = {camera: i for i, camera in enumerate(self.cameras)}
        for tool in self.tools:
            tool_dict = tool.export_dict()
            tool_dict["camera"] = camera_index_map[tool.camera]
            export_dict["tools"].append(tool_dict)
        # output parameter list
        tool_index_map = {tool: i for i, tool in enumerate(self.tools)}
        parameter_index_map = {param: i for i, param in enumerate(self.parameters)}
        for parameter in self.parameters:
            parameter_dict = parameter.export_dict()
            if parameter.is_measurement():
                parameter_dict["inputs"] = [tool_index_map[parameter.tool_input]]
            elif parameter.is_logical():
                parameter_dict["inputs"] = [parameter_index_map[input] for input in parameter.param_inputs]
            export_dict["parameters"].append(parameter_dict)
        # output plc output tag mapping
        export_dict["plc_map"] = self.plc_map

        return export_dict
