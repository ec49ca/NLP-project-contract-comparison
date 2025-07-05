"""
NER/EL/RE-Optimized Document Preprocessing Tool

This tool specifically preprocesses documents to be optimal for:
- Named Entity Recognition (NER)
- Entity Linking (EL)
- Relation Extraction (RE)

Every transformation is designed to make entities and relationships clearer for GPT-based processing.
"""

import logging
import re
from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path
import unicodedata
import os
import json

# OCR and PDF processing imports (with fallbacks)
try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    import PyPDF2

    PDF_PROCESSING_AVAILABLE = True
except ImportError:
    PDF_PROCESSING_AVAILABLE = False

logger = logging.getLogger(__name__)


class PreprocessDocumentTool:
    """Tool for NER/EL/RE-optimized document preprocessing"""

    def __init__(self):
        self.name = "preprocess_document"
        self.description = "Preprocess documents optimized for NER/EL/RE tasks"

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute NER/EL/RE-optimized preprocessing"""
        try:
            document_content = arguments.get("document_content", "")
            document_type = arguments.get("document_type", "")
            remove_stopwords = arguments.get("remove_stopwords", False)
            normalize_text = arguments.get("normalize_text", True)
            file_path = arguments.get("file_path", "")

            if not document_content and not file_path:
                return {
                    "error": "Missing document_content or file_path parameter",
                    "success": False,
                }

            if not document_type:
                return {"error": "Missing document_type parameter", "success": False}

            # Handle OCR for scanned documents
            if file_path and document_type == "scanned":
                processed_content, ocr_success = await self._process_scanned_document(
                    file_path
                )
                if not ocr_success:
                    return {
                        "error": "Failed to process scanned document",
                        "success": False,
                    }
            else:
                processed_content = document_content

            # Apply NER/EL/RE-optimized preprocessing
            processed_content = self._preprocess_for_ner_el_re(
                processed_content, document_type
            )

            # Apply final text normalization
            if normalize_text:
                processed_content = self._normalize_for_entities(processed_content)

            # Optional stopword removal (usually not recommended for NER/EL/RE)
            if remove_stopwords:
                processed_content = self._selective_stopword_removal(processed_content)

            # Generate metadata
            metadata = self._generate_ner_metadata(
                document_content, processed_content, document_type
            )

            result = {
                "processed_content": processed_content,
                "original_length": len(document_content) if document_content else 0,
                "processed_length": len(processed_content),
                "document_type": document_type,
                "preprocessing_applied": {
                    "ner_el_re_optimized": True,
                    "normalization": normalize_text,
                    "stopword_removal": remove_stopwords,
                },
                "metadata": metadata,
                "success": True,
            }

            return result

        except Exception as e:
            logger.error(f"Error in NER/EL/RE preprocessing: {e}")
            return {"error": f"Preprocessing failed: {str(e)}", "success": False}

    def _preprocess_for_ner_el_re(self, content: str, document_type: str) -> str:
        """Route to appropriate NER/EL/RE preprocessing based on document type"""

        if document_type == "html":
            return self._html_to_entity_text(content)
        elif document_type == "markdown":
            return self._markdown_to_entity_text(content)
        elif document_type == "json":
            return self._json_to_entity_sentences(content)
        elif document_type == "csv":
            return self._csv_to_entity_sentences(content)
        elif document_type in ["highly_structured", "structured"]:
            return self._structured_to_entity_text(content)
        elif document_type in ["semi_structured", "moderately_structured"]:
            return self._semi_structured_to_entity_text(content)
        elif document_type in ["unstructured", "highly_unstructured"]:
            return self._unstructured_to_entity_text(content)
        else:
            return self._generic_to_entity_text(content)

    def _html_to_entity_text(self, content: str) -> str:
        """Convert HTML to clean structured format"""
        # Remove scripts and styles
        content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
        content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL)

        records = []
        current_record = []
        record_num = 1

        # Extract and process HTML elements
        elements = []

        # Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", content, re.DOTALL)
        if title_match:
            elements.append(("DOCUMENT_TITLE", title_match.group(1).strip()))

        # Extract headers
        for match in re.finditer(r"<h([1-6])[^>]*>(.*?)</h\1>", content, re.DOTALL):
            level = match.group(1)
            text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            elements.append(("HEADER", f"Level {level}: {text}"))

        # Extract lists
        for match in re.finditer(r"<li[^>]*>(.*?)</li>", content, re.DOTALL):
            text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            elements.append(("LIST_ITEM", text))

        # Extract paragraphs
        for match in re.finditer(r"<p[^>]*>(.*?)</p>", content, re.DOTALL):
            text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            if text:
                elements.append(("CONTENT", text))

        # Extract addresses
        for match in re.finditer(r"<address[^>]*>(.*?)</address>", content, re.DOTALL):
            text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            elements.append(("ADDRESS", text))

        # Extract time elements
        for match in re.finditer(
            r'<time[^>]*datetime="([^"]*)"[^>]*>(.*?)</time>', content
        ):
            datetime_val = match.group(1)
            text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            elements.append(("DATETIME", f"{text} ({datetime_val})"))

        # Extract links
        for match in re.finditer(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', content):
            url = match.group(1)
            text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            elements.append(("LINK", f"{text} [{url}]"))

        # Extract table data
        table_data = self._extract_html_tables_clean(content)
        if table_data:
            elements.extend(table_data)

        # Build records from elements
        for element_type, element_text in elements:
            if element_type == "DOCUMENT_TITLE":
                if current_record:
                    records.append(
                        f"RECORD_{record_num}:\n" + "\n".join(current_record)
                    )
                    current_record = []
                    record_num += 1
                current_record = [f"DOCUMENT_TITLE: {element_text}"]
            elif element_type == "HEADER":
                if current_record:
                    records.append(
                        f"RECORD_{record_num}:\n" + "\n".join(current_record)
                    )
                    current_record = []
                    record_num += 1
                current_record = [f"SECTION_HEADER: {element_text}"]
            else:
                current_record.append(f"{element_type}: {element_text}")

                # Create records every 4-5 elements
                if len(current_record) >= 4:
                    records.append(
                        f"RECORD_{record_num}:\n" + "\n".join(current_record)
                    )
                    current_record = []
                    record_num += 1

        if current_record:
            records.append(f"RECORD_{record_num}:\n" + "\n".join(current_record))

        return "\n\n".join(records)

    def _extract_html_tables_clean(self, content: str) -> List[Tuple[str, str]]:
        """Extract HTML tables in clean format"""
        elements = []
        table_pattern = r"<table[^>]*>(.*?)</table>"
        tables = re.findall(table_pattern, content, re.DOTALL)

        for table_num, table in enumerate(tables, 1):
            # Extract headers
            header_pattern = r"<th[^>]*>(.*?)</th>"
            headers = re.findall(header_pattern, table)
            headers = [re.sub(r"<[^>]+>", "", h).strip() for h in headers]

            # Extract rows
            row_pattern = r"<tr[^>]*>(.*?)</tr>"
            rows = re.findall(row_pattern, table, re.DOTALL)

            record_num = 1
            for row in rows:
                cell_pattern = r"<td[^>]*>(.*?)</td>"
                cells = re.findall(cell_pattern, row)
                cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]

                if headers and cells and len(headers) == len(cells):
                    # Create structured record for each table row
                    table_record = f"TABLE_{table_num}_RECORD_{record_num}:"
                    elements.append(("TABLE_HEADER", table_record))

                    for header, cell in zip(headers, cells):
                        if cell.strip():
                            field_name = self._normalize_field_name(header)
                            elements.append(("TABLE_FIELD", f"{field_name}: {cell}"))

                    record_num += 1

        return elements

    def _extract_html_tables_as_relationships(self, content: str) -> str:
        """Convert HTML tables to explicit entity relationships"""
        table_pattern = r"<table[^>]*>(.*?)</table>"
        tables = re.findall(table_pattern, content, re.DOTALL)

        for table in tables:
            # Extract headers
            header_pattern = r"<th[^>]*>(.*?)</th>"
            headers = re.findall(header_pattern, table)

            # Extract rows
            row_pattern = r"<tr[^>]*>(.*?)</tr>"
            rows = re.findall(row_pattern, table, re.DOTALL)

            table_text = "TABLE_DATA: "
            for row in rows:
                cell_pattern = r"<td[^>]*>(.*?)</td>"
                cells = re.findall(cell_pattern, row)

                if headers and cells and len(headers) == len(cells):
                    relationships = []
                    for header, cell in zip(headers, cells):
                        if cell.strip():
                            relationships.append(f"{header.strip()} is {cell.strip()}")
                    if relationships:
                        table_text += f"RECORD: {'; '.join(relationships)}. "

            # Replace table with entity text
            content = content.replace(table, table_text)

        return content

    def _markdown_to_entity_text(self, content: str) -> str:
        """Convert Markdown to clean structured format"""
        lines = content.split("\n")
        records = []
        current_record = []
        record_num = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Convert headers to sections
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                header_text = line.lstrip("# ").strip()
                if current_record:
                    records.append("\n".join(current_record))
                    current_record = []
                    record_num += 1
                current_record = [
                    f"SECTION_{record_num}:",
                    f"HEADER_LEVEL: {level}",
                    f"TITLE: {header_text}",
                ]

            # Convert lists to items
            elif line.startswith(("* ", "- ", "+ ")) or re.match(r"^\d+\.\s", line):
                item_text = re.sub(r"^[\*\-\+\d]+\.?\s*", "", line)
                item_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", item_text)  # Remove bold
                item_text = re.sub(r"\*([^*]+)\*", r"\1", item_text)  # Remove italic
                current_record.append(f"LIST_ITEM: {item_text}")

            # Convert links
            elif "[" in line and "](" in line:
                link_text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"LINK: \1", line)
                current_record.append(f"CONTENT: {link_text}")

            # Regular content
            else:
                # Remove markdown formatting
                clean_line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
                clean_line = re.sub(r"\*([^*]+)\*", r"\1", clean_line)
                clean_line = re.sub(r"`([^`]+)`", r"\1", clean_line)
                if clean_line:
                    current_record.append(f"CONTENT: {clean_line}")

        if current_record:
            records.append("\n".join(current_record))

        return "\n\n".join(records)

    def _json_to_entity_sentences(self, content: str) -> str:
        """Convert JSON to explicit entity-relationship sentences"""
        try:
            data = json.loads(content)
            return self._json_object_to_sentences(data)
        except:
            return self._generic_to_entity_text(content)

    def _json_object_to_sentences(self, data, context_path="") -> str:
        """Recursively convert JSON to clean structured format"""
        if isinstance(data, dict):
            record_lines = []

            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)):
                    field_name = self._normalize_field_name(key)
                    record_lines.append(f"{field_name}: {value}")
                elif isinstance(value, list):
                    if value:
                        field_name = self._normalize_field_name(key)
                        list_items = [str(item) for item in value]
                        record_lines.append(f"{field_name}: {', '.join(list_items)}")
                elif isinstance(value, dict):
                    # Handle nested objects
                    nested_data = self._json_object_to_sentences(value, key)
                    if nested_data:
                        record_lines.append(f"{self._normalize_field_name(key)}_DATA:")
                        record_lines.append(nested_data)

            return "\n".join(record_lines)

        elif isinstance(data, list):
            records = []
            for i, item in enumerate(data, 1):
                record_data = self._json_object_to_sentences(item)
                if record_data:
                    records.append(f"RECORD_{i}:\n{record_data}")

            return "\n\n".join(records)

        return str(data)

    def _normalize_field_name(self, field_name: str) -> str:
        """Normalize field names to CAPS_WITH_UNDERSCORES format"""
        # Convert to uppercase and replace spaces/hyphens with underscores
        normalized = field_name.upper()
        normalized = re.sub(r"[\s\-]+", "_", normalized)
        normalized = re.sub(
            r"[^\w]", "", normalized
        )  # Remove special chars except underscores

        # Handle common entity type mappings
        if any(
            word in normalized
            for word in ["CUSTOMER_ID", "USER_ID", "EMPLOYEE_ID", "ID"]
        ):
            if not normalized.endswith("_ID") and normalized != "ID":
                normalized = (
                    normalized.replace("ID", "_ID")
                    if "ID" in normalized
                    else f"{normalized}_ID"
                )
        elif "NAME" in normalized:
            normalized = "ENTITY_NAME" if normalized == "NAME" else normalized
        elif any(word in normalized for word in ["EMAIL", "PHONE", "ADDRESS"]):
            pass  # Keep as is
        elif any(word in normalized for word in ["DATE", "TIME"]):
            pass  # Keep as is
        elif any(
            word in normalized
            for word in ["AMOUNT", "PRICE", "COST", "REVENUE", "SALARY"]
        ):
            pass  # Keep as is
        elif any(
            word in normalized for word in ["COMPANY", "ORGANIZATION", "DEPARTMENT"]
        ):
            pass  # Keep as is

        return normalized

    def _csv_to_entity_sentences(self, content: str) -> str:
        """Convert CSV to clean structured entity records"""
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if not lines:
            return content

        # Parse headers
        headers = [h.strip().strip('"') for h in lines[0].split(",")]
        records = []

        for row_num, line in enumerate(lines[1:], 1):
            values = [v.strip().strip('"') for v in line.split(",")]
            if len(values) != len(headers):
                continue

            # Create structured record
            record_lines = [f"RECORD_{row_num}:"]

            for header, value in zip(headers, values):
                if not value or value.lower() in ["", "null", "none", "n/a"]:
                    continue

                # Normalize field names to CAPS_WITH_UNDERSCORES
                field_name = self._normalize_field_name(header)
                record_lines.append(f"{field_name}: {value}")

            records.append("\n".join(record_lines))

        return "\n\n".join(records)

    def _structured_to_entity_text(self, content: str) -> str:
        """Convert structured documents to clean record format"""
        lines = content.split("\n")
        records = []
        current_record = []
        record_num = 1
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect tables
            if "|" in line and line.count("|") >= 2:
                cells = [cell.strip() for cell in line.split("|") if cell.strip()]
                if len(cells) >= 2:
                    # Convert table row to structured format
                    if len(cells) == 2:  # Key-value pair
                        field_name = self._normalize_field_name(cells[0])
                        current_record.append(f"{field_name}: {cells[1]}")
                    else:  # Multi-column data
                        for i in range(0, len(cells), 2):
                            if i + 1 < len(cells):
                                field_name = self._normalize_field_name(cells[i])
                                current_record.append(f"{field_name}: {cells[i+1]}")
                continue

            # Detect sections
            if line.isupper() or (line.endswith(":") and len(line.split()) <= 6):
                if current_record:
                    records.append(
                        f"RECORD_{record_num}:\n" + "\n".join(current_record)
                    )
                    current_record = []
                    record_num += 1
                current_section = line.rstrip(":")
                current_record = [f"SECTION: {current_section}"]
                continue

            # Detect key-value pairs
            if ":" in line and len(line.split(":")) == 2:
                key, value = line.split(":", 1)
                key, value = key.strip(), value.strip()
                field_name = self._normalize_field_name(key)
                current_record.append(f"{field_name}: {value}")
                continue

            # Regular text
            current_record.append(f"CONTENT: {line}")

        if current_record:
            records.append(f"RECORD_{record_num}:\n" + "\n".join(current_record))

        return "\n\n".join(records)

    def _semi_structured_to_entity_text(self, content: str) -> str:
        """Convert semi-structured text to clean record format"""
        lines = content.split("\n")
        records = []
        current_record = []
        record_num = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect headers and sections
            if line.isupper() and len(line.split()) <= 8:
                if current_record:
                    records.append(
                        f"RECORD_{record_num}:\n" + "\n".join(current_record)
                    )
                    current_record = []
                    record_num += 1
                current_record = [f"SECTION_HEADER: {line}"]
            elif line.endswith(":") and len(line.split()) <= 6:
                if current_record:
                    records.append(
                        f"RECORD_{record_num}:\n" + "\n".join(current_record)
                    )
                    current_record = []
                    record_num += 1
                current_record = [f"SUBSECTION: {line[:-1]}"]
            elif ":" in line and len(line.split(":")) == 2:
                # Key-value pairs
                key, value = line.split(":", 1)
                field_name = self._normalize_field_name(key.strip())
                current_record.append(f"{field_name}: {value.strip()}")
            else:
                current_record.append(f"CONTENT: {line}")

        if current_record:
            records.append(f"RECORD_{record_num}:\n" + "\n".join(current_record))

        return "\n\n".join(records)

    def _unstructured_to_entity_text(self, content: str) -> str:
        """Optimize unstructured text for entity extraction"""
        # Split into sentences
        sentences = re.split(r"[.!?]+", content)
        records = []
        current_record = []
        record_num = 1

        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                # Ensure proper capitalization
                sentence = (
                    sentence[0].upper() + sentence[1:]
                    if len(sentence) > 1
                    else sentence.upper()
                )
                current_record.append(f"CONTENT: {sentence}")

                # Create records every 3-5 sentences for better parsing
                if len(current_record) >= 4:
                    records.append(
                        f"RECORD_{record_num}:\n" + "\n".join(current_record)
                    )
                    current_record = []
                    record_num += 1

        if current_record:
            records.append(f"RECORD_{record_num}:\n" + "\n".join(current_record))

        return "\n\n".join(records)

    def _generic_to_entity_text(self, content: str) -> str:
        """Generic entity optimization"""
        # Clean whitespace
        content = re.sub(r"\s+", " ", content)

        # Ensure sentence boundaries for entity extraction
        content = re.sub(r"([a-z])([A-Z])", r"\1. \2", content)

        # Split into lines and create records
        lines = content.split("\n")
        records = []
        current_record = []
        record_num = 1

        for line in lines:
            line = line.strip()
            if line:
                current_record.append(f"CONTENT: {line}")

                # Create records every 3-4 lines for better parsing
                if len(current_record) >= 3:
                    records.append(
                        f"RECORD_{record_num}:\n" + "\n".join(current_record)
                    )
                    current_record = []
                    record_num += 1

        if current_record:
            records.append(f"RECORD_{record_num}:\n" + "\n".join(current_record))

        return "\n\n".join(records)

    def _ensure_sentence_ending(self, text: str) -> str:
        """Ensure text ends with proper punctuation for entity extraction"""
        text = text.strip()
        if text and not text.endswith((".", "!", "?", ":")):
            text += "."
        return text

    def _finalize_entity_text(self, content: str) -> str:
        """Final cleanup for entity extraction optimization"""
        # Clean up multiple spaces
        content = re.sub(r"\s+", " ", content)

        # Ensure proper sentence separation
        content = re.sub(r"\.([A-Z])", r". \1", content)

        # Clean up multiple periods
        content = re.sub(r"\.+", ".", content)

        return content.strip()

    def _normalize_for_entities(self, content: str) -> str:
        """Normalize text specifically for entity recognition"""
        # Unicode normalization
        content = unicodedata.normalize("NFKD", content)

        # Remove control characters but preserve structure
        content = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", content)

        # Normalize quotes (important for entity boundaries)
        content = re.sub(r'[""' "`]", '"', content)

        # Normalize dashes and hyphens
        content = re.sub(r"[–—]", "-", content)

        # Normalize whitespace
        content = re.sub(r"\s+", " ", content)

        return content.strip()

    def _selective_stopword_removal(self, content: str) -> str:
        """Remove only non-essential stopwords (preserve those important for entities)"""
        # Only remove the most common articles/prepositions that don't affect entity recognition
        minimal_stopwords = {
            "a",
            "an",
            "the",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
        }

        words = content.split()
        filtered_words = []

        for i, word in enumerate(words):
            # Don't remove stopwords if they're part of potential entity names
            if (
                word.lower() in minimal_stopwords
                and i > 0
                and i < len(words) - 1
                and not (words[i - 1][0].isupper() and words[i + 1][0].isupper())
            ):
                continue
            filtered_words.append(word)

        return " ".join(filtered_words)

    async def _process_scanned_document(self, file_path: str) -> Tuple[str, bool]:
        """Process scanned documents with OCR including PDFs"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return "", False

            try:
                import pytesseract
                from PIL import Image, ImageEnhance, ImageFilter
            except ImportError as e:
                logger.error(f"OCR libraries not available: {e}")
                return "", False

            file_ext = Path(file_path).suffix.lower()
            logger.info(f"Processing scanned document: {file_path} (type: {file_ext})")

            if file_ext == ".pdf":
                # Handle PDF files
                return await self._process_pdf_with_ocr(file_path)

            elif file_ext in [
                ".png",
                ".jpg",
                ".jpeg",
                ".tiff",
                ".bmp",
                ".gif",
                ".webp",
            ]:
                # Handle image files
                return await self._process_image_with_ocr(file_path)

            else:
                logger.warning(f"Unsupported file type for OCR: {file_ext}")
                return "", False

        except Exception as e:
            logger.error(f"Error in OCR processing: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return "", False

    async def _process_pdf_with_ocr(self, file_path: str) -> Tuple[str, bool]:
        """Process PDF with OCR - handles both text and scanned PDFs"""
        try:
            # First, try to extract existing text from PDF
            existing_text = self._extract_pdf_text(file_path)

            # Check if PDF has sufficient text content (not scanned)
            if existing_text and len(existing_text.strip()) > 100:
                # PDF already has text, check if it's meaningful
                word_count = len(existing_text.split())
                if word_count > 20:  # Threshold for meaningful text
                    logger.info(
                        f"PDF {file_path} already has text content, skipping OCR"
                    )
                    return existing_text, True

            # PDF appears to be scanned, convert to images and OCR
            logger.info(f"PDF {file_path} appears to be scanned, performing OCR")

            try:
                from pdf2image import convert_from_path
            except ImportError:
                logger.error("pdf2image library not available")
                return "", False

            # Convert PDF pages to images
            try:
                images = convert_from_path(
                    file_path, dpi=300
                )  # High DPI for better OCR
                logger.info(f"Converted PDF to {len(images)} images")
            except Exception as e:
                logger.error(f"Failed to convert PDF to images: {e}")
                return "", False

            # OCR each page
            all_text = []
            total_confidence = 0
            pages_processed = 0

            for page_num, image in enumerate(images, 1):
                logger.info(f"Processing page {page_num}/{len(images)}")

                # OCR this page
                page_text, confidence = await self._ocr_single_image(
                    image, f"page_{page_num}"
                )

                if page_text:
                    all_text.append(f"PAGE_{page_num}:\n{page_text}")
                    total_confidence += confidence
                    pages_processed += 1
                else:
                    logger.warning(f"No text extracted from page {page_num}")

            if all_text:
                combined_text = "\n\n".join(all_text)
                avg_confidence = (
                    total_confidence / pages_processed if pages_processed > 0 else 0
                )
                logger.info(
                    f"PDF OCR completed. Pages: {pages_processed}, Avg confidence: {avg_confidence:.2f}"
                )
                return combined_text, True
            else:
                logger.error("No text extracted from any PDF page")
                return "", False

        except Exception as e:
            logger.error(f"Error in PDF OCR processing: {e}")
            return "", False

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract existing text from PDF (if any)"""
        try:
            import PyPDF2

            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text = ""

                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text() + "\n"

                return text.strip()

        except Exception as e:
            logger.warning(f"Failed to extract text from PDF: {e}")
            return ""

    async def _process_image_with_ocr(self, file_path: str) -> Tuple[str, bool]:
        """Process single image file with OCR"""
        try:
            # Load and enhance image for better OCR
            image = Image.open(file_path)
            logger.info(f"Original image size: {image.size}, mode: {image.mode}")

            # OCR the image
            text, confidence = await self._ocr_single_image(image, file_path)

            if text:
                logger.info(
                    f"Image OCR completed for {file_path}. Confidence: {confidence:.2f}"
                )
                return text, True
            else:
                logger.error(f"No text extracted from image {file_path}")
                return "", False

        except Exception as e:
            logger.error(f"Error in image OCR: {e}")
            return "", False

    async def _ocr_single_image(
        self, image: Image, source_name: str
    ) -> Tuple[str, float]:
        """OCR a single PIL Image with enhanced processing"""
        try:
            import pytesseract

            # Convert to grayscale if needed
            if image.mode != "L":
                image = image.convert("L")

            # Enhance image for better OCR results
            # Increase contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)

            # Increase sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)

            # Apply slight blur to reduce noise
            image = image.filter(ImageFilter.MedianFilter(size=3))

            # Try multiple OCR configurations for best results
            ocr_configs = [
                "--oem 3 --psm 6",  # Default config
                "--oem 3 --psm 4",  # Single column of text
                "--oem 3 --psm 3",  # Fully automatic page segmentation
                "--oem 3 --psm 1",  # Automatic page segmentation with OSD
            ]

            best_text = ""
            best_confidence = 0

            for config in ocr_configs:
                try:
                    # Get OCR result with confidence data
                    data = pytesseract.image_to_data(
                        image, config=config, output_type=pytesseract.Output.DICT
                    )

                    # Calculate average confidence
                    confidences = [int(conf) for conf in data["conf"] if int(conf) > 0]
                    avg_confidence = (
                        sum(confidences) / len(confidences) if confidences else 0
                    )

                    # Get text
                    text = pytesseract.image_to_string(image, config=config)

                    logger.info(
                        f"OCR Config: {config}, Confidence: {avg_confidence:.2f}, Text length: {len(text)}"
                    )

                    if avg_confidence > best_confidence and len(text.strip()) > 0:
                        best_text = text
                        best_confidence = avg_confidence

                except Exception as config_error:
                    logger.warning(f"OCR config failed {config}: {config_error}")
                    continue

            return best_text.strip(), best_confidence

        except Exception as e:
            logger.error(f"Error in single image OCR: {e}")
            return "", 0.0

    def _generate_ner_metadata(
        self, original: str, processed: str, doc_type: str
    ) -> Dict[str, Any]:
        """Generate metadata focused on NER/EL/RE metrics"""
        # Count potential entities
        entity_markers = len(
            re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", processed)
        )

        # Count structured markers
        structure_markers = len(
            re.findall(
                r"(ENTITY_|ATTRIBUTE:|SECTION:|TEMPORAL_|FINANCIAL_|CONTACT_|ORGANIZATION_)",
                processed,
            )
        )

        return {
            "original_length": len(original) if original else 0,
            "processed_length": len(processed),
            "compression_ratio": len(processed) / len(original) if original else 0,
            "document_type": doc_type,
            "sentence_count": len(re.split(r"[.!?]+", processed)),
            "potential_entities": entity_markers,
            "structure_markers": structure_markers,
            "entity_density": (
                entity_markers / len(processed.split()) if processed.split() else 0
            ),
            "ner_optimized": True,
        }
