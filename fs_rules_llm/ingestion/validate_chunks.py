"""
Chunk Validator for Formula Student Rules.

Validates that chunks meet quality requirements:
- Have all required metadata fields
- Fall within word count limits
- Have identifiers where expected
- Don't contain corrupted text
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import json


@dataclass
class ValidationError:
    """Represents a validation error for a chunk."""
    chunk_id: str
    error_type: str
    message: str
    severity: str  # "error" or "warning"


class ChunkValidator:
    """
    Validates rule chunks for quality and completeness.
    
    Ensures chunks meet all requirements before indexing:
    - Required metadata present
    - Word count within limits
    - Clause IDs where expected
    - No corrupted or empty text
    """
    
    # Required fields that must be present and non-empty
    REQUIRED_FIELDS = [
        'chunk_id',
        'document_name',
        'season',
        'competition',
        'chunk_text',
        'page_number'
    ]
    
    # Fields that should be present (can be empty)
    OPTIONAL_FIELDS = [
        'section_title',
        'clause_id',
        'is_table',
        'word_count'
    ]
    
    def __init__(
        self,
        min_words: int = 150,
        max_words: int = 400,
        strict: bool = True
    ):
        """
        Initialize validator.
        
        Args:
            min_words: Minimum acceptable word count
            max_words: Maximum acceptable word count
            strict: If True, reject chunks with warnings. If False, only errors.
        """
        self.min_words = min_words
        self.max_words = max_words
        self.strict = strict
    
    def validate_chunks(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[ValidationError]]:
        """
        Validate a list of chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Tuple of (valid_chunks, validation_errors)
        """
        valid_chunks = []
        all_errors = []
        
        for chunk in chunks:
            errors = self.validate_chunk(chunk)
            
            # Determine if chunk should be rejected
            has_errors = any(e.severity == "error" for e in errors)
            has_warnings = any(e.severity == "warning" for e in errors)
            
            should_reject = has_errors or (self.strict and has_warnings)
            
            if should_reject:
                all_errors.extend(errors)
            else:
                valid_chunks.append(chunk)
                # Still collect warnings for reporting
                all_errors.extend([e for e in errors if e.severity == "warning"])
        
        return valid_chunks, all_errors
    
    def validate_chunk(self, chunk: Dict[str, Any]) -> List[ValidationError]:
        """
        Validate a single chunk.
        
        Args:
            chunk: Chunk dictionary
            
        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors = []
        chunk_id = chunk.get('chunk_id', 'UNKNOWN')
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in chunk:
                errors.append(ValidationError(
                    chunk_id=chunk_id,
                    error_type="missing_field",
                    message=f"Missing required field: {field}",
                    severity="error"
                ))
            elif field == 'page_number':
                # page_number can be 0 but must be an integer
                if not isinstance(chunk[field], int):
                    errors.append(ValidationError(
                        chunk_id=chunk_id,
                        error_type="invalid_type",
                        message=f"Field {field} must be an integer",
                        severity="error"
                    ))
            elif not chunk[field]:  # Empty or None
                errors.append(ValidationError(
                    chunk_id=chunk_id,
                    error_type="empty_field",
                    message=f"Required field is empty: {field}",
                    severity="error"
                ))
        
        # If we have errors, don't continue validation
        if errors:
            return errors
        
        # Validate chunk text
        text = chunk['chunk_text']
        
        # Check for corrupted text patterns
        if self._is_corrupted(text):
            errors.append(ValidationError(
                chunk_id=chunk_id,
                error_type="corrupted_text",
                message="Chunk text appears corrupted (excessive special characters)",
                severity="error"
            ))
        
        # Validate word count
        word_count = chunk.get('word_count', len(text.split()))
        
        # Tables can be shorter
        is_table = chunk.get('is_table', False)
        
        if not is_table and word_count < self.min_words:
            errors.append(ValidationError(
                chunk_id=chunk_id,
                error_type="too_short",
                message=f"Chunk has {word_count} words, minimum is {self.min_words}",
                severity="warning"
            ))
        
        if word_count > self.max_words:
            errors.append(ValidationError(
                chunk_id=chunk_id,
                error_type="too_long",
                message=f"Chunk has {word_count} words, maximum is {self.max_words}",
                severity="error"
            ))
        
        # Check for clause_id in non-table chunks
        # This is a warning, not an error, since some chunks might not have clause IDs
        clause_id = chunk.get('clause_id', '')
        if not is_table and not clause_id:
            # Check if the text looks like it should have a clause ID
            if self._should_have_clause_id(text):
                errors.append(ValidationError(
                    chunk_id=chunk_id,
                    error_type="missing_clause_id",
                    message="Chunk appears to contain a rule but has no clause_id",
                    severity="warning"
                ))
        
        # Validate season and competition format
        season = chunk.get('season', '')
        if season and not season.isdigit():
            errors.append(ValidationError(
                chunk_id=chunk_id,
                error_type="invalid_season",
                message=f"Season should be a year (e.g., '2024'), got: {season}",
                severity="warning"
            ))
        
        return errors
    
    def _is_corrupted(self, text: str) -> bool:
        """
        Check if text appears corrupted.
        
        Heuristics:
        - Too many non-alphanumeric characters
        - Excessive special characters
        - Very short with no readable words
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears corrupted
        """
        if len(text) < 10:
            return True
        
        # Count alphanumeric vs special characters
        alphanumeric = sum(c.isalnum() or c.isspace() for c in text)
        special = len(text) - alphanumeric
        
        # If more than 30% special characters, likely corrupted
        if special / len(text) > 0.3:
            return True
        
        # Check for readable words
        words = text.split()
        readable_words = sum(1 for w in words if len(w) > 2 and w[0].isalpha())
        
        if len(words) > 5 and readable_words / len(words) < 0.5:
            return True
        
        return False
    
    def _should_have_clause_id(self, text: str) -> bool:
        """
        Check if text looks like it should have a clause ID.
        
        Heuristics:
        - Contains words like "must", "shall", "required"
        - Starts with a capital letter and looks like a rule statement
        
        Args:
            text: Text to check
            
        Returns:
            True if text looks like a rule that should have a clause ID
        """
        rule_keywords = [
            'must', 'shall', 'required', 'requirement',
            'prohibited', 'not permitted', 'mandatory'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in rule_keywords)


def validate_chunks_file(
    input_file: str,
    output_file: str,
    errors_file: str = None,
    min_words: int = 150,
    max_words: int = 400,
    strict: bool = True
) -> Tuple[int, int, int]:
    """
    Validate chunks from a JSON file.
    
    Args:
        input_file: Path to input JSON with chunks
        output_file: Path to save valid chunks
        errors_file: Optional path to save validation errors
        min_words: Minimum word count
        max_words: Maximum word count
        strict: Strict validation mode
        
    Returns:
        Tuple of (total_chunks, valid_chunks, error_count)
    """
    # Load chunks
    with open(input_file, 'r') as f:
        chunks = json.load(f)
    
    # Validate
    validator = ChunkValidator(min_words, max_words, strict)
    valid_chunks, errors = validator.validate_chunks(chunks)
    
    # Save valid chunks
    with open(output_file, 'w') as f:
        json.dump(valid_chunks, f, indent=2)
    
    # Save errors if requested
    if errors_file and errors:
        errors_dict = [
            {
                'chunk_id': e.chunk_id,
                'error_type': e.error_type,
                'message': e.message,
                'severity': e.severity
            }
            for e in errors
        ]
        with open(errors_file, 'w') as f:
            json.dump(errors_dict, f, indent=2)
    
    return len(chunks), len(valid_chunks), len(errors)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate Formula Student rule chunks"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to JSON file with chunks"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to save valid chunks"
    )
    parser.add_argument(
        "--errors",
        help="Path to save validation errors (optional)"
    )
    parser.add_argument(
        "--min-words",
        type=int,
        default=150,
        help="Minimum chunk size in words (default: 150)"
    )
    parser.add_argument(
        "--max-words",
        type=int,
        default=400,
        help="Maximum chunk size in words (default: 400)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: reject chunks with warnings"
    )
    
    args = parser.parse_args()
    
    print(f"Validating chunks from: {args.input}")
    print(f"Strict mode: {args.strict}")
    
    total, valid, error_count = validate_chunks_file(
        args.input,
        args.output,
        args.errors,
        args.min_words,
        args.max_words,
        args.strict
    )
    
    print(f"\nValidation complete:")
    print(f"  Total chunks: {total}")
    print(f"  Valid chunks: {valid}")
    print(f"  Rejected: {total - valid}")
    print(f"  Issues found: {error_count}")
    
    if args.errors and error_count > 0:
        print(f"  Errors saved to: {args.errors}")
    
    print(f"\nValid chunks saved to: {args.output}")
