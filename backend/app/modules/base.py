"""
Abstract base class for diagnostic modules.
Defines the plugin interface for all diagnostic modules.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel


class DiagnosisResult(BaseModel):
    """Standard diagnosis result schema."""
    diagnosis: str  # "normal" | "dysplasia" | "subluxation" | "dislocation"
    confidence: float
    side_affected: str  # "none" | "left" | "right" | "bilateral"


class EducationalData(BaseModel):
    """Educational output with detailed analysis data."""
    keypoints: Dict[str, Any]  # Detected anatomical landmarks
    masks: Dict[str, Any]  # Segmentation masks as polygons
    lines: Dict[str, Any]  # Geometric lines and equations
    measurements_left: Dict[str, Any] = {}
    measurements_right: Dict[str, Any] = {}


class BaseDiagnosticModule(ABC):
    """
    Abstract base class for diagnostic modules.
    Each module (hip_dysplasia, scoliosis, etc.) inherits from this.
    """
    
    module_name: str = "base"
    
    def __init__(self, models: Dict[str, Any]):
        """
        Initialize diagnostic module with loaded ML models.
        
        Args:
            models: Dictionary of loaded ML models from app.state
        """
        self.models = models
    
    @abstractmethod
    async def analyze(self, image_data: bytes, patient_age: int = None, 
                     patient_sex: str = None) -> Dict[str, Any]:
        """
        Analyze medical image and return diagnosis.
        
        Args:
            image_data: Binary image data (DICOM or JPG/PNG)
            patient_age: Optional patient age from DICOM metadata
            patient_sex: Optional patient sex
            
        Returns:
            Dictionary with:
            - result: DiagnosisResult
            - educational_data: EducationalData
            - metadata: Processing details
        """
        pass
    
    @abstractmethod
    def validate_input(self, image_data: bytes) -> bool:
        """Validate that image is suitable for this module."""
        pass
