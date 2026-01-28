"""
Audit Mode for Formula Student Rules.

Exposes all retrieved context and provides detailed reasoning trace.
Used for debugging and verification.
"""

import sys
from pathlib import Path
from typing import Dict, Any
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from query.answer_generator import AnswerGenerator, create_answer_generator


class AuditMode:
    """
    Audit mode handler for debugging and verification.
    
    Shows:
    - All retrieved chunks with metadata
    - Relevance analysis
    - Detailed reasoning trace
    - Final answer with full citations
    """
    
    def __init__(self, generator: AnswerGenerator):
        """
        Initialize audit mode.
        
        Args:
            generator: AnswerGenerator instance
        """
        self.generator = generator
    
    def audit_question(self, question: str) -> Dict[str, Any]:
        """
        Perform detailed audit of a question.
        
        Args:
            question: User's question
            
        Returns:
            Complete audit report
        """
        # Generate answer using audit mode
        result = self.generator.generate_answer(question, mode="audit")
        
        # Build comprehensive audit report
        report = {
            'question': question,
            'season': self.generator.retriever.season,
            'competition': self.generator.retriever.competition,
            'chunks_retrieved': result['chunks_retrieved'],
            'retrieved_chunks': self._format_chunks(result.get('chunks', [])),
            'answer': result['answer'],
            'citations': result.get('citations', []),
            'validation': result['validation'],
            'prompt_used': result.get('prompt', '')
        }
        
        return report
    
    def _format_chunks(self, chunks: list) -> list:
        """
        Format chunks for audit display.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List of formatted chunk dictionaries
        """
        formatted = []
        
        for i, chunk in enumerate(chunks, 1):
            formatted.append({
                'rank': i,
                'chunk_id': chunk.get('chunk_id', 'N/A'),
                'document': chunk.get('document_name', 'Unknown'),
                'season': chunk.get('season', 'N/A'),
                'competition': chunk.get('competition', 'N/A'),
                'section': chunk.get('section_title', 'N/A'),
                'clause_id': chunk.get('clause_id', 'N/A'),
                'page': chunk.get('page_number', 'N/A'),
                'is_table': chunk.get('is_table', False),
                'word_count': chunk.get('word_count', 0),
                'text': chunk.get('chunk_text', '')
            })
        
        return formatted
    
    def print_audit_report(self, report: Dict[str, Any]):
        """
        Print formatted audit report.
        
        Args:
            report: Audit report dictionary
        """
        print("\n" + "=" * 80)
        print("AUDIT REPORT")
        print("=" * 80)
        print(f"\nQuestion: {report['question']}")
        print(f"Season: {report['season']}")
        print(f"Competition: {report['competition']}")
        print(f"\nChunks Retrieved: {report['chunks_retrieved']}")
        
        print("\n" + "-" * 80)
        print("RETRIEVED CHUNKS:")
        print("-" * 80)
        
        for chunk in report['retrieved_chunks']:
            print(f"\n[{chunk['rank']}] {chunk['clause_id']} - {chunk['section']}")
            print(f"    Document: {chunk['document']}")
            print(f"    Page: {chunk['page']}")
            print(f"    Words: {chunk['word_count']}")
            print(f"    Table: {chunk['is_table']}")
            print(f"    Text: {chunk['text'][:300]}...")
            print()
        
        print("-" * 80)
        print("ANSWER:")
        print("-" * 80)
        print(report['answer'])
        
        print("\n" + "-" * 80)
        print("VALIDATION:")
        print("-" * 80)
        print(json.dumps(report['validation'], indent=2))
        
        if report['citations']:
            print("\n" + "-" * 80)
            print("EXTRACTED CITATIONS:")
            print("-" * 80)
            for citation in report['citations']:
                print(f"  - {citation}")
        
        print("\n" + "=" * 80)


def run_audit_mode(
    season: str,
    competition: str,
    question: str
) -> Dict[str, Any]:
    """
    Convenience function to run audit mode.
    
    Args:
        season: Season identifier
        competition: Competition identifier
        question: Question to audit
        
    Returns:
        Audit report dictionary
    """
    generator = create_answer_generator(season, competition)
    audit = AuditMode(generator)
    return audit.audit_question(question)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Audit mode for Formula Student rules compliance system"
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
        "--question",
        required=True,
        help="Question to audit"
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output file"
    )
    
    args = parser.parse_args()
    
    report = run_audit_mode(
        args.season,
        args.competition,
        args.question
    )
    
    # Print report
    audit = AuditMode(None)
    audit.print_audit_report(report)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {args.output}")
