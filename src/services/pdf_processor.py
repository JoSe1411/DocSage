import PyPDF2
import pdfplumber
from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter

class PDFProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
    
    def extract_text(self, pdf_path: str) -> str:
        """Extract text from PDF using pdfplumber for better accuracy"""
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
        
    def chunk_text(self, text: str) -> List[Dict[str, any]]:
        """Split text into chunks for vector storage"""
        chunks = self.text_splitter.create_documents([text])
        return [
            {"content": chunk.page_content, "chunk_index": i}
            for i, chunk in enumerate(chunks)
        ]
