import threading

_model = None
_lock  = threading.Lock()


def initialize_model():
    """Load ArcFace model into memory once at startup."""
    global _model
    with _lock:
        if _model is None:
            print("⏳ Loading ArcFace model into memory...")
            from deepface import DeepFace
            # Warm up the model by running a dummy representation
            import numpy as np
            dummy = np.zeros((224, 224, 3), dtype=np.uint8)
            try:
                DeepFace.represent(
                    img_path       = dummy,
                    model_name     = "ArcFace",
                    detector_backend = "mtcnn",  # Fast detector for warmup
                    enforce_detection = False
                )
            except Exception:
                pass
            _model = True
            print("✅ ArcFace model loaded and ready!")


def is_model_ready():
    return _model is not None