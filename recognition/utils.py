import os
import io
import json
import numpy as np
from PIL import Image
from deepface import DeepFace
from sklearn.metrics.pairwise import cosine_similarity
from django.conf import settings


# ─── CONFIGURATION ────────────────────────────────────────────────────────────
MODEL_NAME       = "ArcFace"        # Most robust model for makeup/contacts
DETECTOR_BACKEND = "mtcnn"     # Best face detector
THUMBNAIL_SIZE   = (200, 200)       # Compressed storage size
JPEG_QUALITY     = 75               # 75% JPEG quality
MATCH_THRESHOLD  = 0.68             # Cosine distance — lower = stricter
# ──────────────────────────────────────────────────────────────────────────────


def extract_embedding(image_path: str) -> list:
    """
    Extract a 512-D ArcFace embedding from an image.
    Always called on the ORIGINAL full-quality image before compression.
    
    Returns:
        list: 512-element embedding vector
    
    Raises:
        ValueError: If no face is detected in the image
    """
    try:
        result = DeepFace.represent(
            img_path    = image_path,
            model_name  = MODEL_NAME,
            detector_backend = DETECTOR_BACKEND,
            enforce_detection = True   # Raise error if no face found
        )
        return result[0]["embedding"]  # 512-D vector

    except Exception as e:
        raise ValueError(f"No face detected or processing failed: {str(e)}")


def compress_image(image_path: str, save_path: str) -> str:
    """
    Compress image to 200x200 JPEG at 75% quality.
    Used AFTER embedding extraction — only for display purposes.
    
    Args:
        image_path: Path to original image
        save_path:  Where to save compressed thumbnail
    
    Returns:
        str: Path to saved compressed image
    """
    img = Image.open(image_path).convert("RGB")
    img = img.resize(THUMBNAIL_SIZE, Image.LANCZOS)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    img.save(save_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

    return save_path


def compress_image_from_memory(pil_image: Image.Image, save_path: str) -> str:
    """
    Same as compress_image but accepts a PIL Image object directly.
    Used when image comes from an upload (InMemoryUploadedFile).
    """
    img = pil_image.convert("RGB")
    img = img.resize(THUMBNAIL_SIZE, Image.LANCZOS)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    img.save(save_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

    return save_path


def cosine_distance(vec1: list, vec2: list) -> float:
    """
    Compute cosine distance between two embedding vectors.
    0.0 = identical faces, 1.0 = completely different.
    """
    v1 = np.array(vec1).reshape(1, -1)
    v2 = np.array(vec2).reshape(1, -1)
    similarity = cosine_similarity(v1, v2)[0][0]
    return 1 - similarity   # Convert similarity → distance


def find_matches(query_image_path: str) -> list:
    """
    Compare a query face against ALL stored embeddings in the database.
    
    Args:
        query_image_path: Path to the query/search image
    
    Returns:
        List of dicts sorted by confidence (highest first):
        [
            {
                "person_name": "John Doe",
                "person_id": 1,
                "face_id": 3,
                "confidence": 94.2,
                "image_url": "/media/faces/thumbnails/john.jpg"
            },
            ...
        ]
    """
    from .models import FaceRecord  # Import here to avoid circular import

    # Step 1: Extract embedding from query image (full quality)
    query_embedding = extract_embedding(query_image_path)

    matches = []

    # Step 2: Compare against every stored embedding
    for record in FaceRecord.objects.select_related('person').all():
        stored_embedding = record.embedding  # Already a list from JSONField
        distance = cosine_distance(query_embedding, stored_embedding)

        if distance < MATCH_THRESHOLD:
            confidence = round((1 - distance) * 100, 2)
            matches.append({
                "person_name" : record.person.name,
                "person_id"   : record.person.id,
                "face_id"     : record.pk,
                "confidence"  : confidence,
                "distance"    : round(distance, 4),
                "image_url"   : record.image.url,
            })

    # Step 3: Sort by confidence descending
    matches.sort(key=lambda x: x["confidence"], reverse=True)

    # Step 4: Deduplicate — keep only best match per person
    seen_persons = set()
    unique_matches = []
    for match in matches:
        if match["person_id"] not in seen_persons:
            seen_persons.add(match["person_id"])
            unique_matches.append(match)

    return unique_matches