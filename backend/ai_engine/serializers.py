from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        # Return all fields to the React frontend
        fields = ['id', 'title', 'file', 'uploaded_at', 'processed', 'user']
        # Prevent users from manually setting the 'user' or 'processed' status during upload
        read_only_fields = ['user', 'processed']