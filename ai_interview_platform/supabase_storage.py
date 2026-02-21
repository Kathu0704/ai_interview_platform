# ai_interview_platform/supabase_storage.py
import os
from supabase import create_client
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class SupabaseStorage(Storage):
    def __init__(self):
        url = os.environ.get('SUPABASE_URL')
        key = os.environ.get('SUPABASE_ANON_KEY')
        self.client = create_client(url, key)
        self.bucket = 'resumes'

    def _save(self, name, content):
        file_bytes = content.read()
        # Remove 'resumes/' prefix if present (bucket is already 'resumes')
        file_name = name.replace('resumes/', '')
        self.client.storage.from_(self.bucket).upload(
            file_name,
            file_bytes,
            {"content-type": "application/pdf", "upsert": "true"}
        )
        return name

    def url(self, name):
        file_name = name.replace('resumes/', '')
        res = self.client.storage.from_(self.bucket).get_public_url(file_name)
        return res

    def exists(self, name):
        return False  # Always allow upload

    def delete(self, name):
        file_name = name.replace('resumes/', '')
        try:
            self.client.storage.from_(self.bucket).remove([file_name])
        except Exception as e:
            print(f"Supabase delete error: {e}")
