import logging

from ultralytics import YOLO
from pathlib import Path
from core.camera import Camera

logger = logging.getLogger(__name__)

class VisionTool:
    """
    Base class for all vision tools.
    
    Args:
        name (str): Display name of the tool.
        camera (Camera): Camera object associated with the tool.
        tool_type (str): Type of tool ('detect', 'classify', etc.).
        render_settings (dict): Attributes for GUI rendering results.
        
    Methods:
        get_frame(): Obtain a numpy array frame from the connected camera if it is running.
        start(): Start inference thread.
        stop(): Stop inference thread.
        _inference_loop(): Run inference on camera frames. Update latest results.
        get_results(): Return a dict of vision results.
        export_dict(): Return a dict containing tool config data.
    """
    
    def __init__(self,name:str,camera: Camera,tool_type: str,render_settings: dict):
        self.name = name
        self.camera = camera
        self.tool_type = tool_type
        self.render_settings = render_settings

        self.latest_results = None

        logger.debug(f"Created vision tool {self}.")

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name},camera={self.camera},tool_type={self.tool_type},render_settings={self.render_settings})"

    def get_frame(self):
        """
        Obtain a numpy array frame from the connected camera if it is running.

        Returns (numpy array): Frame obtained from camera.
        """
        if not self.camera.is_running:
            return None
        else:
            return self.camera.get_last_frame()

    def get_results(self):
        raise NotImplementedError
    
    def export_dict(self):
        """Returns: a dict containing tool config data"""
        return {
            "tool_type": self.tool_type,
            "name": self.name,
            "camera": 0, # overwritten by vision project export
            "render": self.render_settings
        }

class DetectTool(VisionTool):
    """
    Vision Tool for YOLO detection models.

    Args:
        name (str): Display name of the tool.
        camera (Camera): Camera object associated with the tool.
        tool_type (str): Type of tool ('detect', 'classify', etc.).
        model_path (str): file path of model used for inference.

    Methods:
        get_frame(): Obtain a numpy array frame from the connected camera if it is running.
        _inference_loop(): Run inference on camera frames. Update latest results.
        get_results(): Return a list of dict containing score, class, corners of detected objects.
        export_dict(): Return a dict containing tool config data
    """

    def __init__(self, name: str, camera: Camera, render_settings, model_path: Path):
        super().__init__(name, camera, "detect", render_settings)
        self.model_name = None
        self.model = None
        if model_path:
            self.set_model(model_path)

    def set_model(self,model_path: Path):
        self.model_name = model_path.name
        self.model = YOLO(model_path,task="detect")

    def predict_results(self):
        """Returns (list: dict): list of dict containing score, class, x, y, w, h of detected objects."""
        frame = self.get_frame()

        if frame is None:
            return None
        
        if self.model is None:
            return None

        # Get inference results
        results_list = []
        round_precision = 4
        results = self.model.predict(frame,verbose=False)[0].boxes

        for score,cls,outline in zip(results.conf,results.cls,results.xyxyn):
            x1,y1,x2,y2 = outline.tolist()
            class_id = int(cls)
            results_list.append({
                "score":round(float(score),3),
                "class_id": class_id,
                "x1":round(x1, round_precision),
                "y1":round(y1, round_precision),
                "x2":round(x2, round_precision),
                "y2":round(y2, round_precision)
            })

        self.latest_results = results_list
    
    def get_results(self):
        if self.latest_results is None:
            return None
        else:
            return self.latest_results
    
    def export_dict(self):
        """Returns (dict): a dict containing tool config data"""
        config = super().export_dict()
        config["model"] = self.model_name
        return config