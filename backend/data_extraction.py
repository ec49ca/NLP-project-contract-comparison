"""
Data Extraction Utility - Uploads WIPO PDFs to Pinecone vector database.

This script:
1. Reads PDFs from backend/uploads/wipo_documents/
2. Extracts text using PyPDF2
3. Chunks text using tiktoken (token-based chunking)
4. Generates OpenAI embeddings
5. Uploads to Pinecone index

Usage:
    python -m backend.data_extraction

Environment Variables Required:
    OPENAI_API_KEY - OpenAI API key for embeddings
    PINECONE_API_KEY - Pinecone API key for vector database
"""

import os
from pinecone import Pinecone, ServerlessSpec
from PyPDF2 import PdfReader
from openai import OpenAI
import tiktoken
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PDF_FOLDER = "backend/uploads/wipo_documents"
INDEX_NAME = "wipo-index"

MODEL = "text-embedding-3-small"
TOKEN_LIMIT = 400  # keep chunks small => safe Pinecone metadata

# Get API keys from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")


def load_pdf(path: str) -> str:
	"""Extract the full text from a PDF."""
	reader = PdfReader(path)
	text = ""
	for page in reader.pages:
		text += page.extract_text() or ""
	return text


def token_chunk(text, max_tokens=TOKEN_LIMIT):
	"""Split text into token-limited chunks using tiktoken."""
	enc = tiktoken.encoding_for_model(MODEL)
	tokens = enc.encode(text)

	chunks = []
	start = 0

	while start < len(tokens):
		end = start + max_tokens
		token_slice = tokens[start:end]
		chunk_text = enc.decode(token_slice)

		# avoid empty chunks
		if chunk_text.strip():
			chunks.append(chunk_text)

		start = end

	return chunks


def embed_chunks(chunks):
	"""Generate embeddings for text chunks."""
	client = OpenAI(api_key=OPENAI_API_KEY)

	response = client.embeddings.create(
		model=MODEL,
		input=chunks
	)

	return [d.embedding for d in response.data]


def upload_to_pinecone(index, file_name, country, chunks, embeddings):
	"""Upload embeddings with safe metadata including text."""
	vectors = []

	for i, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):

		vectors.append({
			"id": f"{file_name}-{i}",
			"values": emb,
			"metadata": {
				"file_name": file_name,
				"chunk_id": i,
				"country": country,
				"text": chunk_text  # SAFE because chunks are tiny (<1kb)
			}
		})

	index.upsert(vectors=vectors)
	print(f"✓ Uploaded {len(vectors)} chunks for {file_name}")


def main():
	# Validate environment variables
	if not OPENAI_API_KEY:
		raise ValueError("OPENAI_API_KEY environment variable is required")
	if not PINECONE_API_KEY:
		raise ValueError("PINECONE_API_KEY environment variable is required")

	# 1. Initialize Pinecone
	print("🔧 Initializing Pinecone...")
	pc = Pinecone(api_key=PINECONE_API_KEY)

	# 2. Create index if needed
	if INDEX_NAME not in [idx.name for idx in pc.list_indexes()]:
		print(f"📦 Creating index '{INDEX_NAME}'...")
		pc.create_index(
			name=INDEX_NAME,
			dimension=1536,  # embedding-3-small => 1536 dims
			metric="cosine",
			spec=ServerlessSpec(cloud="aws", region="us-east-1"),
		)
		print("✓ Index created.")
	else:
		print(f"✓ Index '{INDEX_NAME}' already exists.")

	index = pc.Index(INDEX_NAME)

	# 3. Process all PDFs
	if not os.path.exists(PDF_FOLDER):
		print(f"⚠️  Warning: {PDF_FOLDER} does not exist. Creating it...")
		os.makedirs(PDF_FOLDER, exist_ok=True)
		print(f"ℹ️  Please add WIPO PDF documents to {PDF_FOLDER} and run this script again.")
		return

	pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]
	
	if not pdf_files:
		print(f"⚠️  No PDF files found in {PDF_FOLDER}")
		print(f"ℹ️  Please add WIPO PDF documents and run this script again.")
		return

	print(f"\n📚 Found {len(pdf_files)} PDF file(s) to process...\n")

	for file in pdf_files:
		print(f"📄 Processing: {file}")

		full_path = os.path.join(PDF_FOLDER, file)

		# Extract PDF text
		print("  → Extracting text...")
		text = load_pdf(full_path)

		# Token-based chunking
		print("  → Chunking text...")
		chunks = token_chunk(text)
		print(f"  → Created {len(chunks)} chunks")

		# Embed
		print("  → Generating embeddings...")
		embeddings = embed_chunks(chunks)

		# Upload
		print("  → Uploading to Pinecone...")
		upload_to_pinecone(
			index=index,
			file_name=file,
			country="Unknown",  # You can modify this to extract from filename or content
			chunks=chunks,
			embeddings=embeddings
		)
		print()

	print("\n✅ DONE — All PDFs processed successfully.")
	print(f"📊 Total documents in index: {index.describe_index_stats()['total_vector_count']}")


if __name__ == "__main__":
	main()

