import os

from rest_framework import serializers
from .models import (
    Document, AcademicPaper, PaperLibrary, ResearchTopic, 
    ResearchGap, PaperQnA
)


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


# ============================================================================
# ACADEMIC PAPER SERIALIZERS
# ============================================================================

class AcademicPaperSerializer(serializers.ModelSerializer):
    """Serializer for academic papers from external sources"""
    class Meta:
        model = AcademicPaper
        fields = [
            'id', 'external_id', 'title', 'abstract', 'authors',
            'publication_year', 'venue', 'doi', 'url', 'pdf_url',
            'citation_count', 'source', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PaperLibrarySerializer(serializers.ModelSerializer):
    """Serializer for paper collections"""
    papers = AcademicPaperSerializer(many=True, read_only=True)
    paper_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PaperLibrary
        fields = [
            'id', 'name', 'description', 'papers', 'paper_count',
            'is_favorite', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_paper_count(self, obj):
        return obj.papers.count()


class ResearchTopicSerializer(serializers.ModelSerializer):
    """Serializer for AI engineering research topics"""
    class Meta:
        model = ResearchTopic
        fields = [
            'id', 'title', 'description', 'relevance_score',
            'relevance_reason', 'key_challenges', 'skills_needed',
            'related_fields', 'papers_count', 'growth_percentage'
        ]
        read_only_fields = ['id']


class ResearchGapSerializer(serializers.ModelSerializer):
    """Serializer for identified research gaps"""
    class Meta:
        model = ResearchGap
        fields = [
            'id', 'title', 'description', 'potential_research_directions',
            'supporting_papers', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PaperQnASerializer(serializers.ModelSerializer):
    """Serializer for paper Q&A interactions"""
    class Meta:
        model = PaperQnA
        fields = [
            'id', 'paper', 'question', 'answer', 'sources_cited',
            'faithfulness_score', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
