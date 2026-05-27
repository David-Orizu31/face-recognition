from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os


class Person(models.Model):
    """Represents a registered individual in the system"""
    name        = models.CharField(max_length=150)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class FaceRecord(models.Model):
    """
    Stores a face image (compressed thumbnail) + its embedding vector.
    The embedding is what actually powers recognition.
    The image is only used for display in results.
    """
    person      = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='faces')
    # Compressed 200x200 JPEG thumbnail — display only
    image       = models.ImageField(upload_to='faces/thumbnails/')
    # Full 512-D ArcFace embedding vector stored as JSON
    embedding   = models.JSONField()
    model_used  = models.CharField(max_length=50, default='ArcFace')
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.person.name} — Face #{self.pk}"
    
@receiver(post_delete, sender=FaceRecord)
def delete_face_image_on_record_delete(sender, instance, **kwargs):
    """
    Automatically deletes image file from /media/ whenever
    a FaceRecord is deleted from anywhere — view, admin, shell, anywhere.
    """
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)