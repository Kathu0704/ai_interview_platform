import os
from django.apps import AppConfig
from django.conf import settings


class CandidateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'candidate'

    def ready(self):
        # Ensure MEDIA_ROOT and resumes/ exist (e.g. when using Render persistent disk)
        try:
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if media_root:
                os.makedirs(os.path.join(media_root, 'resumes'), exist_ok=True)
        except Exception:
            pass
