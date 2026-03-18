"""
In-memory patient data store for demo/prototype.
Can be replaced with a database (PostgreSQL, MongoDB, etc.).
"""
from typing import Dict, Any, List
from datetime import datetime


class PatientStore:
    """Simple in-memory store for patient data and analysis results."""
    
    def __init__(self):
        self.patients: Dict[str, Dict[str, Any]] = {}
        self.results: Dict[str, List[Dict[str, Any]]] = {}
    
    def create_patient(
        self, 
        patient_id: str, 
        name: str = None, 
        age: int = None, 
        sex: str = None
    ) -> Dict[str, Any]:
        """Create or update patient record."""
        self.patients[patient_id] = {
            "patient_id": patient_id,
            "name": name,
            "age": age,
            "sex": sex,
            "created_at": datetime.utcnow().isoformat(),
        }
        self.results[patient_id] = []
        return self.patients[patient_id]
    
    def get_patient(self, patient_id: str) -> Dict[str, Any]:
        """Get patient by ID."""
        return self.patients.get(patient_id)
    
    def get_all_patients(self) -> List[Dict[str, Any]]:
        """Get all patients."""
        return list(self.patients.values())
    
    def add_result(self, patient_id: str, analysis_result: Dict[str, Any]) -> None:
        """Add analysis result for patient."""
        if patient_id not in self.results:
            self.results[patient_id] = []
        
        result_with_meta = {
            **analysis_result,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
        self.results[patient_id].append(result_with_meta)
    
    def get_results(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all analysis results for patient."""
        return self.results.get(patient_id, [])
    
    def get_latest_result(self, patient_id: str) -> Dict[str, Any]:
        """Get latest analysis result for patient."""
        results = self.results.get(patient_id, [])
        return results[-1] if results else None


# Global instance
patient_store = PatientStore()
