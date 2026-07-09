import json
import logging
from pathlib import Path
import random
import re
import shutil
from core.camera import Camera
from core.sv_project import SVProject
from ultralytics import YOLO

logger = logging.getLogger(__name__)

#region Model Project
class ModelProject(SVProject):
    """
    Base class for a Model Project.
    Holds data for training new models/vision tools
    
    Args:
        config_file_path: path to .json config file which holds the data for this project.

    Methods:
        """
    
    ALLOWED_TYPES = {"detect"}
    
    def __init__(self,config_file_path: Path):
        super().__init__(config_file_path)

        if self.project_type not in ModelProject.ALLOWED_TYPES:
            raise ValueError(f"Invalid project type: {self.project_type}")

        # Currently connected camera
        self.opening_camera = False
        self.camera = Camera.from_dict(self.project_config.get("camera"))
    
    def start_camera(self):
        self.opening_camera = True
        self.camera.start_connection()
        self.opening_camera = False

#region Detect Project
class DetectProject(ModelProject):
    """
    Class which holds data for creating new Detect models
    
    Args:
        config_file_path: path to .json config file which holds the data for this project.

    Methods:
        """
    
    def __init__(self, config_file_path):
        super().__init__(config_file_path)

        # class display data
        self.classes = self.project_config.get("classes")

        # load saved annotations - dict of image_name, boxes
        self.annotations = self.project_config.get("annotations")

        # model training
        self.train_settings = self.project_config.get("train")

        # get base model path (if single file in base_model directory, use it; otherwise None)
        self.base_model_path = None
        base_model_dir = self.project_folder_path / "base_model"
        if base_model_dir.exists():
            files = [f for f in base_model_dir.iterdir() if f.is_file()]

            if len(files) == 1:
                self.base_model_path = files[0]

        self.model_export_dir = self.train_settings.get("export_path")
        if self.model_export_dir is not None:
            self.model_export_dir = Path(self.model_export_dir)

    def generate_yaml(self):
        dataset_path = self.project_folder_path / "dataset"

        # generate yaml file
        with open(dataset_path / "data.yaml",mode="w") as f:
            f.write(f"path: {dataset_path}\n")
            f.write("train: images/train\n")
            f.write("val: images/val\n")
            f.write("test: images/test\n")
            f.write(f"nc: {len(self.classes)}\n")
            f.write("names:\n")
            for i, cls in enumerate(self.classes):
                f.write(f"  {i}: {cls['name']}\n")

    def generate_label(self, img_filename: Path, split_category):
        lbl_save_path = self.project_folder_path / "dataset" / "labels" / split_category / f"{img_filename.stem}.txt"
        lbl_save_path.parent.mkdir(parents=True,exist_ok=True)

        id_map = {cls["id"]: idx for idx,cls in enumerate(self.classes)}

        with open(lbl_save_path, 'w') as f:
            anns = self.annotations.get(f"{img_filename.name}",[])
            for ann in anns:
                x_center = (ann["x2"] + ann["x1"]) / 2
                y_center = (ann["y2"] + ann["y1"]) / 2
                box_w = (ann["x2"] - ann["x1"])
                box_h = (ann["y2"] - ann["y1"])

                f.write(f"{id_map[ann['class_id']]} {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}\n")
    
    def format_dataset_yolo(self):
        logger.debug(f"Formatting dataset.")

        imgs_path = self.project_folder_path / "raw_images"
        dataset_path = self.project_folder_path / "dataset"

        # clear old dataset
        if dataset_path.exists():
            shutil.rmtree(dataset_path)
        dataset_path.mkdir(parents=True,exist_ok=True)

        # split images by proportion
        img_filetypes = {".jpg",".jpeg",".png",".bmp"}

        images = [f for f in imgs_path.iterdir() if f.suffix.lower() in img_filetypes]
        random.seed(42)
        random.shuffle(images)

        splits = {
            "train": 0.7,
            "val": 0.2,
            "test": 0.1
        }

        n = len(images)
        train_end = int(n * splits["train"])
        val_end = train_end + int(n * splits["val"])

        split_map = {
            "train": images[:train_end],
            "val": images[train_end:val_end],
            "test": images[val_end:]
        }

        for split, files in split_map.items():
            (dataset_path / "images" / split).mkdir(parents=True,exist_ok=True)
            (dataset_path / "labels" / split).mkdir(parents=True,exist_ok=True)

            for img_file in files:
                # copy image to dataset
                shutil.copy(img_file, dataset_path / "images" / split / img_file.name)

                # create label file
                self.generate_label(img_file, split)

        self.generate_yaml()

        logger.debug(f"Formatted dataset.")

    def generate_model_filename(self,name:str):
        name = name.strip().replace(" ","_")

        name = re.sub(r'[<>:"/\\|?*]','',name)

        name = re.sub(r'[^A-Za-z0-9._-]','',name)

        return name or "model"
    
    def train_model(self,on_train_start=None,on_epoch_end=None,on_train_end=None):
        logger.debug(f"Training model.")
        # format dataset
        self.format_dataset_yolo()
        dataset_yaml = self.project_folder_path / "dataset" / "data.yaml"
        settings = self.train_settings

        # load model
        model = YOLO(self.base_model_path)

        # add callbacks
        if on_train_start:
            model.add_callback("on_train_start",on_train_start)
        if on_epoch_end:
            model.add_callback("on_train_epoch_end",on_epoch_end)
        if on_train_end:
            model.add_callback("on_train_end",on_train_end)

        # train
        results = model.train(
            data=str(dataset_yaml),
            epochs=settings.get("epochs",100),
            imgsz=settings.get("imgsz",640),
            batch=settings.get("batch",8),
            conf=settings.get("conf",0.25),
            augment=settings.get("augment",True),
            multi_scale=settings.get("multiscale",False),
            # freeze=settings.get("freeze",0),
            project=str(self.project_folder_path / "dataset"),
            exist_ok=True,
            plots=False
        )

        # save best model
        best_model_path = Path(results.save_dir) / "weights" / "best.pt"

        if best_model_path.exists():
            model_name = self.generate_model_filename(self.project_name)
            self.model_export_dir.mkdir(parents=True,exist_ok=True)
            dest_path = self.model_export_dir / f"{model_name}.pt"

            # avoid overwriting existing
            counter = 1
            while dest_path.exists():
                dest_path = self.model_export_dir / f"{model_name}_{counter}.pt"
                counter += 1

            shutil.copy(best_model_path, dest_path)

        # export render file
        if settings.get("export_render_file",True):
            render_file_path = dest_path.with_name(f"{dest_path.stem}_render.json")               

            with open(render_file_path, "w", encoding="utf-8") as f:
                json.dump(self.classes, f, indent=2)

        self.edited = True

    def export_model(self,base_model: Path,output_format: str, output_location: Path, on_complete=None):
        logger.debug(f"Exporting model {base_model}")
        model = YOLO(base_model)

        self.exported_model_path = Path(model.export(format=output_format,project=output_location,name="",exist_ok=True))

        logger.debug(f"Exported model: {self.exported_model_path}")
        if on_complete:
            on_complete()

    def export_dict(self):
        export_dict = {
            **super().export_dict(),
            "camera": self.camera.export_dict(),
            "classes": self.classes,
            "annotations": self.annotations,
            "train": self.train_settings
        }

        return export_dict