from pypdf import PdfReader
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentService:
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def process_document(self, file_path: str, filename: str) -> list[str]:
        """Extract text from PDF or text file and chunk it."""
        text = self._extract_text(file_path, filename)
        chunks = self.splitter.split_text(text)
        return chunks
    
    def _extract_text(self, file_path: str, filename: str) -> str:
        """Extract text from PDF or TXT file."""
        if filename.lower().endswith('.pdf'):
            return self._extract_from_pdf(file_path)
        elif filename.lower().endswith('.txt'):
            return self._extract_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {filename}")
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF."""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
