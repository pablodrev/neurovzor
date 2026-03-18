"""
Hip Dysplasia diagnostic module.
Analyzes X-ray images for hip dysplasia using YOLO segmentation and geometric analysis.
"""
import logging
from typing import Dict, Any, Optional
from io import BytesIO
import numpy as np
import cv2

from app.modules.base import BaseDiagnosticModule

logger = logging.getLogger(__name__)


class HipDysplasiaModule(BaseDiagnosticModule):
    """Hip dysplasia diagnostic module."""
    
    module_name = "hip_dysplasia"
    CLASSES = {
        0: "femur",
        1: "pubis_ischium", 
        2: "ilium",
    }
    
    async def analyze(
        self, 
        image_data: bytes, 
        patient_age: int = None, 
        patient_sex: str = None
    ) -> Dict[str, Any]:
        """
        Analyze X-ray image for hip dysplasia.
        
        Steps:
        1. Load image (DICOM or JPG/PNG)
        2. Extract metadata (age)
        3. Run YOLO segmentation
        4. Compute geometric measurements
        5. Determine diagnosis
        """
        try:
            # Step 1: Load and validate image
            image_array, metadata = self._load_image(image_data)
            if patient_age is None and 'patient_age' in metadata:
                patient_age = metadata['patient_age']
            
            logger.info(f"Image loaded: {image_array.shape}")
            
            # Step 2: Run YOLO segmentation
            yolo = self.models.get('yolo')
            if yolo is None:
                raise RuntimeError("YOLO model not loaded")
            
            segmentation_results = self._run_segmentation(image_array, yolo)
            
            logger.info(f"Segmentation complete: found {len(segmentation_results)} masks")
            
            # Geometric calculations
            from app.modules.hip_dysplasia.calculations import compute_measurements
            measurements, keypoints = compute_measurements(image_array, segmentation_results)
            
            # Step 5: Format response
            return {
                "patient_id": metadata.get('patient_id', 'UNKNOWN'),
                "module": self.module_name,
                "status": "success",
                "result": {
                    "diagnosis": self._determine_diagnosis(measurements),
                    "confidence": 0.88,
                    "side_affected": self._determine_side(measurements),
                },
                "educational_data": {
                    "keypoints": keypoints,
                    "masks": self._format_masks(segmentation_results),
                    "lines": measurements.get('lines', {}),
                    "measurements_left": measurements.get('left', {}),
                    "measurements_right": measurements.get('right', {}),
                },
                "metadata": {
                    "patient_age": patient_age,
                    "patient_sex": patient_sex,
                    "image_size": image_array.shape,
                }
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return {
                "module": self.module_name,
                "status": "error",
                "error": str(e),
            }
    
    def validate_input(self, image_data: bytes) -> bool:
        """Validate image format (DICOM or JPG/PNG)."""
        try:
            # Check for DICOM magic number
            if image_data.startswith(b'\x00\x00\x00\x00DICM'):
                return True
            # Check for JPEG magic number
            if image_data.startswith(b'\xff\xd8\xff'):
                return True
            # Check for PNG magic number
            if image_data.startswith(b'\x89PNG'):
                return True
            return False
        except Exception:
            return False
    
    def _load_image(self, image_data: bytes) -> tuple:
        """Load image from bytes and extract metadata."""
        metadata = {'patient_id': f'PT-{np.random.randint(1000, 9999)}'}
        
        # Try DICOM first
        try:
            import pydicom
            dicom_file = pydicom.dcmread(BytesIO(image_data))
            
            # Extract age if available
            if hasattr(dicom_file, 'PatientAge'):
                age_str = str(dicom_file.PatientAge)
                # Parse age format (e.g., "045Y" -> 45)
                if age_str and age_str[-1] in 'YMD':
                    metadata['patient_age'] = int(age_str[:-1])
            
            # Get pixel array
            image_array = dicom_file.pixel_array.astype(np.float32)
            
            # Normalize to 0-255 if needed
            if image_array.max() > 255:
                image_array = (image_array / image_array.max() * 255).astype(np.uint8)
            elif image_array.max() <= 1:
                image_array = (image_array * 255).astype(np.uint8)
            
            logger.info(f"Loaded DICOM image: {image_array.shape}")
            return image_array, metadata
            
        except Exception as e:
            logger.debug(f"Not DICOM: {e}, trying PIL...")
        
        # Fallback to PIL for JPG/PNG
        try:
            from PIL import Image
            image = Image.open(BytesIO(image_data)).convert('L')  # Convert to grayscale
            image_array = np.array(image, dtype=np.uint8)
            logger.info(f"Loaded PIL image: {image_array.shape}")
            return image_array, metadata
        except Exception as e:
            raise ValueError(f"Failed to load image: {e}")
    
    def _run_segmentation(self, image_array: np.ndarray, yolo) -> list:
        """Run YOLO segmentation on image."""
        from app.core.config import settings
        
        # YOLO expects RGB or BGR, convert if grayscale
        if len(image_array.shape) == 2:
            image_rgb = np.stack([image_array] * 3, axis=-1)
        else:
            image_rgb = image_array
        
        # Run inference
        results = yolo(
            image_rgb,
            conf=settings.YOLO_CONF_THRESHOLD,
            iou=settings.YOLO_IOU_THRESHOLD,
            verbose=False,
        )
        
        # Extract masks as polygons
        segmentations = []
        if results[0].masks is not None:
            H, W = image_array.shape[:2]
            for idx, mask in enumerate(results[0].masks):
                class_id = int(results[0].boxes.cls[idx]) if results[0].boxes is not None else 0
                
                # Get mask as binary array and find contour
                mask_data = mask.data[0].cpu().numpy() if hasattr(mask.data, 'cpu') else mask.data[0]
                mask_bin = (mask_data > 0.5).astype(np.uint8)
                
                # Find contours
                contours, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    contour = max(contours, key=cv2.contourArea)
                    polygon = contour.reshape(-1, 2).tolist()
                    
                    segmentations.append({
                        'mask': polygon,
                        'class': self.CLASSES.get(class_id, 'unknown'),
                        'class_id': class_id,
                        'confidence': float(results[0].boxes.conf[idx]) if results[0].boxes is not None else 0.9,
                    })
        
        return segmentations

    
    def _format_masks(self, segmentations: list) -> Dict[str, Any]:
        """Format segmentation masks for frontend."""
        masks = {}
        for seg in segmentations:
            class_name = seg['class']
            if class_name not in masks:
                masks[class_name] = []
            masks[class_name].append({
                'polygon': seg['mask'],
                'confidence': seg['confidence'],
            })
        return masks
    
    def _determine_diagnosis(self, measurements: Dict) -> str:
        """Determine diagnosis from measurements."""
        left_severity = measurements.get('left', {}).get('diagnosis_severity', 'normal')
        right_severity = measurements.get('right', {}).get('diagnosis_severity', 'normal')
        
        if left_severity == 'dysplasia' or right_severity == 'dysplasia':
            return 'dysplasia'
        return 'normal'
    
    def _determine_side(self, measurements: Dict) -> str:
        """Determine which side is affected."""
        left_severity = measurements.get('left', {}).get('diagnosis_severity', 'normal')
        right_severity = measurements.get('right', {}).get('diagnosis_severity', 'normal')
        
        if left_severity != 'normal' and right_severity != 'normal':
            return 'bilateral'
        elif left_severity != 'normal':
            return 'left'
        elif right_severity != 'normal':
            return 'right'
        return 'none'
