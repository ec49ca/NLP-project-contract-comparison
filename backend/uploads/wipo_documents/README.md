# WIPO Documents Directory

This directory contains WIPO (World Intellectual Property Organization) PDF documents for external agent semantic search.

## Purpose

These documents are:
1. Processed by `backend/data_extraction.py`
2. Chunked into token-based segments
3. Embedded using OpenAI's `text-embedding-3-small` model
4. Uploaded to Pinecone vector database
5. Queried by the External Agent for semantic search

## Usage

### Adding Documents

1. Place WIPO PDF documents in this directory
2. Run the data extraction script:
   ```bash
   python -m backend.data_extraction
   ```
3. The script will process all PDFs and upload them to Pinecone

### Requirements

- OPENAI_API_KEY environment variable (for embeddings)
- PINECONE_API_KEY environment variable (for vector database)

### Document Format

- File type: PDF
- Content: WIPO legal documents, compliance guides, regional requirements
- Recommended naming: descriptive names (e.g., `it236en_1.pdf` for Italy WIPO document)

## Current Documents

This directory currently contains sample WIPO documents for testing and demonstration purposes.

## Notes

- Documents are chunked into ~400 token segments for optimal retrieval
- Each chunk is embedded and stored with metadata (file_name, chunk_id, country, text)
- The External Agent performs semantic search across all uploaded documents
- Top 5 most relevant chunks are retrieved for each query

