"""
PDF Parser for Formula Student Rules Documents.

Layout-aware PDF parsing that preserves:
- Section headers
- Clause numbers
- Tables
- Page numbers
"""

import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import pdfplumber
from dataclasses import dataclass


@dataclass
class ParsedSection:
    """
    Represents a parsed section from a PDF.
    
    Attributes:
        text: The raw text content
        page_number: Source page number
        section_title: Detected section title (if any)
        clause_id: Detected clause ID like "T.2.3.1" (if any)
        is_table: Whether this is a table
        table_data: Table data if is_table is True
    """
    text: str
    page_number: int
    section_title: Optional[str] = None
    clause_id: Optional[str] = None
    is_table: bool = False
    table_data: Optional[List[List[str]]] = None


class PDFParser:
    """
    Layout-aware PDF parser for Formula Student rulebooks.
    
    Extracts structured content while preserving:
    - Section hierarchy
    - Clause numbering
    - Tables as standalone elements
    - Metadata for each section
    """
    
    # Regex patterns for detecting structure
    # Common FS rule formats: T.2.3.1, A.1.2, IN.3.4, etc.
    CLAUSE_PATTERN = re.compile(r'\b([A-Z]{1,3})\.(\d+\.)*\d+\b')
    
    # Section headers are typically ALL CAPS or Title Case with numbers
    SECTION_PATTERN = re.compile(r'^([A-Z\s\d\.]+)$', re.MULTILINE)
    
    def __init__(self, pdf_path: str):
        """
        Initialize PDF parser.
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.document_name = self.pdf_path.name
    
    def parse(self) -> List[ParsedSection]:
        """
        Parse the PDF and extract structured sections.
        
        Returns:
            List of ParsedSection objects
        """
        sections = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract tables first (they should be standalone)
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        if table and len(table) > 0:
                            sections.append(self._create_table_section(
                                table, page_num
                            ))
                
                # Extract text
                text = page.extract_text()
                if text:
                    # Split text into paragraphs/sections
                    text_sections = self._split_into_sections(text, page_num)
                    sections.extend(text_sections)
        
        return sections
    
    def _create_table_section(
        self, 
        table: List[List[str]], 
        page_number: int
    ) -> ParsedSection:
        """
        Create a ParsedSection for a table.
        
        Args:
            table: Table data as list of rows
            page_number: Page number where table appears
            
        Returns:
            ParsedSection with table data
        """
        # Convert table to text representation
        text_lines = []
        for row in table:
            # Filter out None values and join with | separator
            cleaned_row = [str(cell) if cell else "" for cell in row]
            text_lines.append(" | ".join(cleaned_row))
        
        text = "\n".join(text_lines)
        
        # Try to detect clause ID in table content
        clause_id = self._extract_clause_id(text)
        
        return ParsedSection(
            text=text,
            page_number=page_number,
            is_table=True,
            table_data=table,
            clause_id=clause_id
        )
    
    def _split_into_sections(
        self, 
        text: str, 
        page_number: int
    ) -> List[ParsedSection]:
        """
        Split page text into logical sections.
        
        This is a simplified approach. In production, you might want to:
        - Use more sophisticated heading detection
        - Preserve formatting and indentation
        - Handle multi-column layouts
        
        Args:
            text: Page text
            page_number: Page number
            
        Returns:
            List of ParsedSection objects
        """
        sections = []
        
        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_section_title = None
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Check if this is a section header
            # Headers are typically short, ALL CAPS, or numbered
            lines = para.split('\n')
            first_line = lines[0].strip()
            
            is_header = (
                len(first_line) < 100 and  # Short
                (first_line.isupper() or  # ALL CAPS
                 re.match(r'^\d+\.?\s+[A-Z]', first_line))  # Numbered heading
            )
            
            if is_header and len(lines) == 1:
                # This is likely a section header
                current_section_title = first_line
                continue
            
            # Extract clause ID if present
            clause_id = self._extract_clause_id(para)
            
            sections.append(ParsedSection(
                text=para,
                page_number=page_number,
                section_title=current_section_title,
                clause_id=clause_id
            ))
        
        return sections
    
    def _extract_clause_id(self, text: str) -> Optional[str]:
        """
        Extract clause ID from text if present.
        
        Formula Student rules typically use formats like:
        - T.2.3.1 (Technical rules)
        - A.1.2 (Administrative rules)
        - IN.3.4 (Inspection rules)
        
        Args:
            text: Text to search
            
        Returns:
            Clause ID if found, None otherwise
        """
        # Look for clause pattern at the start of text
        first_line = text.split('\n')[0]
        match = self.CLAUSE_PATTERN.search(first_line)
        
        if match:
            return match.group(0)
        
        return None
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the PDF document.
        
        Returns:
            Dictionary with document metadata
        """
        metadata = {
            'document_name': self.document_name,
            'file_path': str(self.pdf_path),
            'file_size_bytes': self.pdf_path.stat().st_size
        }
        
        with pdfplumber.open(self.pdf_path) as pdf:
            metadata['num_pages'] = len(pdf.pages)
            
            # Try to extract PDF metadata
            if pdf.metadata:
                metadata['pdf_metadata'] = pdf.metadata
        
        return metadata


def parse_pdf(
    pdf_path: str,
    season: str,
    competition: str
) -> Dict[str, Any]:
    """
    Convenience function to parse a PDF with metadata.
    
    Args:
        pdf_path: Path to PDF file
        season: Season identifier (e.g., "2024")
        competition: Competition identifier (e.g., "FSAE")
        
    Returns:
        Dictionary with 'sections' and 'metadata' keys
    """
    parser = PDFParser(pdf_path)
    sections = parser.parse()
    metadata = parser.get_metadata()
    
    # Add season and competition to metadata
    metadata['season'] = season
    metadata['competition'] = competition
    
    return {
        'sections': sections,
        'metadata': metadata
    }


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="Parse Formula Student rulebook PDFs"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to PDF file or directory"
    )
    parser.add_argument(
        "--season",
        required=True,
        help="Season identifier (e.g., 2024)"
    )
    parser.add_argument(
        "--competition",
        required=True,
        help="Competition identifier (e.g., FSAE)"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path (optional)"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    # Handle both single file and directory
    if input_path.is_file():
        pdf_files = [input_path]
    elif input_path.is_dir():
        pdf_files = list(input_path.glob("*.pdf"))
    else:
        raise ValueError(f"Input path not found: {args.input}")
    
    if not pdf_files:
        print(f"No PDF files found in {args.input}")
        exit(1)
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    
    all_sections = []
    
    for pdf_file in pdf_files:
        print(f"\nParsing: {pdf_file.name}")
        result = parse_pdf(
            str(pdf_file),
            args.season,
            args.competition
        )
        sections = result['sections']
        metadata = result['metadata']
        print(f"  Extracted {len(sections)} sections")
        print(f"  Pages: {metadata['num_pages']}")
        
        # Convert to dict for serialization
        for section in sections:
            section_dict = {
                'text': section.text,
                'page_number': section.page_number,
                'section_title': section.section_title,
                'clause_id': section.clause_id,
                'is_table': section.is_table,
                'document_name': metadata['document_name'],
                'season': metadata['season'],
                'competition': metadata['competition']
            }
            all_sections.append(section_dict)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(all_sections, f, indent=2)
        print(f"\nSaved {len(all_sections)} sections to {args.output}")
    else:
        print(f"\nParsed {len(all_sections)} total sections")
