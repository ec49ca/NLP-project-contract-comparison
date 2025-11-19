"""
Document Storage Service - Manages uploaded PDF documents and their extracted text.
"""
import os
import pdfplumber
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class DocumentStorage:
	"""Manages document storage and retrieval."""
	
	def __init__(self, upload_dir: str = "backend/uploads"):
		"""
		Initialize document storage.
		
		Args:
			upload_dir: Directory to store uploaded PDFs
		"""
		self.upload_dir = Path(upload_dir)
		self.upload_dir.mkdir(parents=True, exist_ok=True)
		
		# In-memory cache: {filename: {"text": str, "uploaded_at": datetime, "filepath": str}}
		self._documents: Dict[str, Dict] = {}
		
		# Load existing documents on startup
		self._load_existing_documents()
	
	def _load_existing_documents(self):
		"""Load existing PDF files from upload directory."""
		logger.info(f"Loading existing documents from {self.upload_dir}")
		for pdf_file in self.upload_dir.glob("*.pdf"):
			try:
				filename = pdf_file.name
				if filename not in self._documents:
					logger.info(f"Loading existing document: {filename}")
					text = self._extract_text_from_pdf(pdf_file)
					self._documents[filename] = {
						"text": text,
						"uploaded_at": datetime.fromtimestamp(pdf_file.stat().st_mtime),
						"filepath": str(pdf_file)
					}
			except Exception as e:
				logger.error(f"Error loading document {pdf_file.name}: {str(e)}")
	
	def _extract_text_from_pdf(self, pdf_path: Path) -> str:
		"""
		Extract text from a PDF file.
		
		Args:
			pdf_path: Path to PDF file
			
		Returns:
			Extracted text content
		"""
		text_content = []
		try:
			with pdfplumber.open(pdf_path) as pdf:
				for page in pdf.pages:
					page_text = page.extract_text()
					if page_text:
						text_content.append(page_text)
			return "\n\n".join(text_content)
		except Exception as e:
			logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
			raise
	
	def save_document(self, filename: str, file_content: bytes) -> Dict:
		"""
		Save an uploaded PDF document.
		
		Args:
			filename: Original filename
			file_content: PDF file content as bytes
			
		Returns:
			Dict with document info
		"""
		# Sanitize filename
		safe_filename = self._sanitize_filename(filename)
		
		# Save PDF file
		filepath = self.upload_dir / safe_filename
		with open(filepath, "wb") as f:
			f.write(file_content)
		
		# Extract text
		text = self._extract_text_from_pdf(filepath)
		
		# Store in memory
		self._documents[safe_filename] = {
			"text": text,
			"uploaded_at": datetime.now(),
			"filepath": str(filepath)
		}
		
		logger.info(f"Saved document: {safe_filename} ({len(text)} characters)")
		
		return {
			"filename": safe_filename,
			"uploaded_at": self._documents[safe_filename]["uploaded_at"].isoformat(),
			"text_length": len(text)
		}
	
	def _sanitize_filename(self, filename: str) -> str:
		"""
		Sanitize filename to prevent path traversal and ensure uniqueness.
		
		Args:
			filename: Original filename
			
		Returns:
			Sanitized filename
		"""
		# Remove path components
		filename = Path(filename).name
		
		# Add hash if file already exists to ensure uniqueness
		base_name = Path(filename).stem
		extension = Path(filename).suffix
		
		if filename in self._documents:
			# File exists, add hash
			hash_suffix = hashlib.md5(filename.encode()).hexdigest()[:8]
			filename = f"{base_name}_{hash_suffix}{extension}"
		
		return filename
	
	def get_document_text(self, filename: str) -> Optional[str]:
		"""
		Get extracted text for a document.
		
		Args:
			filename: Document filename
			
		Returns:
			Extracted text or None if not found
		"""
		doc = self._documents.get(filename)
		return doc["text"] if doc else None
	
	def get_documents(self, selected_filenames: Optional[List[str]] = None) -> List[Dict]:
		"""
		Get list of documents.
		
		Args:
			selected_filenames: Optional list of filenames to filter by
			
		Returns:
			List of document info dicts
		"""
		docs = []
		for filename, doc_info in self._documents.items():
			if selected_filenames is None or filename in selected_filenames:
				docs.append({
					"filename": filename,
					"uploaded_at": doc_info["uploaded_at"].isoformat(),
					"text_length": len(doc_info["text"])
				})
		return sorted(docs, key=lambda x: x["uploaded_at"], reverse=True)
	
	def get_selected_documents_text(self, selected_filenames: List[str]) -> str:
		"""
		Get combined text from selected documents.
		
		Args:
			selected_filenames: List of filenames to include
			
		Returns:
			Combined text from selected documents
		"""
		texts = []
		for filename in selected_filenames:
			text = self.get_document_text(filename)
			if text:
				texts.append(f"=== Document: {filename} ===\n{text}\n")
		return "\n\n".join(texts)
	
	def delete_document(self, filename: str) -> bool:
		"""
		Delete a document.
		
		Args:
			filename: Document filename to delete
			
		Returns:
			True if deleted, False if not found
		"""
		if filename not in self._documents:
			return False
		
		# Delete file
		filepath = Path(self._documents[filename]["filepath"])
		if filepath.exists():
			filepath.unlink()
		
		# Remove from memory
		del self._documents[filename]
		
		logger.info(f"Deleted document: {filename}")
		return True

