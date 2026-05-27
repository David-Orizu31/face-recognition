from django.apps import AppConfig


class RecognitionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recognition"

    def ready(self):
        """
        Load DeepFace model into memory when Django starts.
        This means the first request is slow but ALL subsequent
        requests are fast.
        """
        from recognition.model_cache import initialize_model
        initialize_model()