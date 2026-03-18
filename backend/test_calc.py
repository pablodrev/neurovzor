"""Quick test of calculations module"""
import numpy as np
import sys

print("Testing calculation module import...")

try:
    from app.modules.hip_dysplasia.calculations import compute_measurements
    print("✅ Calculation module imported")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Create dummy segmentation results
seg_results = [
    {
        "mask": [[100, 100], [200, 100], [200, 200], [100, 200]],
        "class": "femur",
        "confidence": 0.9
    },
    {
        "mask": [[50, 50], [150, 50], [150, 150], [50, 150]],
        "class": "ilium",
        "confidence": 0.93
    },
    {
        "mask": [[200, 200], [250, 200], [250, 250], [200, 250]],
        "class": "pubis_ischium",
        "confidence": 0.88
    },
]

# Create dummy image
image = np.zeros((500, 500), dtype=np.uint8)

try:
    measurements, keypoints = compute_measurements(image, seg_results)
    print("✅ compute_measurements executed successfully")
    print(f"\nMeasurements keys: {measurements.keys()}")
    print(f"Keypoints: {keypoints}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All tests passed!")
