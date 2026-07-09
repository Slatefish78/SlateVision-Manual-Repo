import logging
import time
import cv2
import threading

logger = logging.getLogger(__name__)

class Camera:
    def __init__(self,name:str,source:str,resolution_width:int,resolution_height:int,fps):
        self.name = name

        # check if source is int
        try:
            self.source = int(source)
        except ValueError:
            self.source = source
            
        self.resolution_width = resolution_width
        self.resolution_height = resolution_height
        self.fps = fps

        self.video_capture = None
        self.latest_frame = None
        self.latest_frame_time = None

        self.is_running = False
        self._thread = None
        self._lock = threading.Lock()

        logger.debug(f"Created {self}.")

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name},source={self.source},resolution_width={self.resolution_width},resolution_height={self.resolution_height},fps={self.fps})"

    @classmethod
    def from_dict(cls,data: dict):
        """Init camera object from config dict"""
        return cls(
            name = data["name"],
            source = data["source"],
            resolution_width = data["resolution_width"],
            resolution_height = data["resolution_height"],
            fps = data["fps"]
        )

    def start_connection(self,timeout=None,error_feedback=None):
        """Initialize connection to physical camera and start running in background thread
            
        Raises:
            RuntimeError: Could not open camera """
        logger.debug(f"Starting {self} connection.")

        if self.is_running and self._thread and self._thread.is_alive():
            logger.debug(f"Camera is already running.")
            return
        
        self.end_connection()
        
        #initialize video capture
        self.video_capture = cv2.VideoCapture(self.source)

        if not self.video_capture.isOpened():
            raise RuntimeError("Could not open camera.")

        self.video_capture.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*'MJPG'))
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH,self.resolution_width)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT,self.resolution_height)
        self.video_capture.set(cv2.CAP_PROP_FPS,self.fps)

        self.is_running = True
        self._thread = threading.Thread(
            target=self._stream_loop,
            daemon=True
        )
        self._thread.start()

        start_time = time.time()

        while self.latest_frame is None:
            if timeout is not None and (time.time() - start_time) > timeout:
                self.end_connection()
                raise TimeoutError(f"Timeout ({timeout} seconds) exceeded.")
            
            time.sleep(0.01)

        logger.debug(f"Started {self} connection.")

    def _stream_loop(self):
        while self.is_running:
            ret, frame = self.video_capture.read()
            if ret:
                with self._lock:
                    self.latest_frame = frame
                    self.latest_frame_time = time.time()
            else:
                logger.debug("Camera capture failed. Disconnecting.")
                self.is_running = False
                break

    def end_connection(self):
        """End connection to physical camera. Release video capture, stop background thread"""
        logger.debug(f"Ending {self} connection.")
        self.is_running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10.0)

        self._thread = None

        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None

        self.latest_frame = None

        logger.debug(f"Ended {self} connection.")

    def get_last_frame(self):
        with self._lock:
            if self.latest_frame is None:
                return None
            else:
                return self.latest_frame.copy()
            
    def save_img(self,frame,save_path):
        cv2.imwrite(save_path,frame)

    def export_dict(self):
        return {
            "name": self.name,
            "source":self.source,
            "resolution_width": self.resolution_width,
            "resolution_height": self.resolution_height,
            "fps": self.fps
        }