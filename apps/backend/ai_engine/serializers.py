import os

from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    def validate_file(self, file_obj):
        max_mb = int(os.environ.get("MAX_PDF_UPLOAD_MB", "20"))
        max_bytes = max_mb * 1024 * 1024

        if file_obj.size > max_bytes:
            raise serializers.ValidationError(f"PDF exceeds the {max_mb}MB size limit.")

        filename = (getattr(file_obj, "name", "") or "").lower()
        if not filename.endswith(".pdf"):
            raise serializers.ValidationError("Only .pdf files are allowed.")

        content_type = getattr(file_obj, "content_type", "")
        if content_type and content_type not in {"application/pdf", "application/x-pdf"}:
            raise serializers.ValidationError("Invalid file type. Expected application/pdf.")

        signature = file_obj.read(5)
        file_obj.seek(0)
        if not signature.startswith(b"%PDF-"):
            raise serializers.ValidationError("File content is not a valid PDF.")

        return file_obj

    class Meta:
        model = Document
        # Return all fields to the React frontend
        fields = [
            'id',
            'title',
            'file',
            'uploaded_at',
            'processed',
            'status',
            'progress_percent',
            'total_chunks',
            'processed_chunks',
            'last_error',
            'user',
        ]
        # Prevent users from manually setting the 'user' or 'processed' status during upload
        read_only_fields = [
            'user',
            'processed',
            'status',
            'progress_percent',
            'total_chunks',
            'processed_chunks',
            'last_error',
        ]
