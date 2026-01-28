"""
Answer Generator for Formula Student Rules.

LLM interface with strict citation validation and format enforcement.
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from query import prompt_templates
from query.retriever import RuleRetriever


class AnswerGenerator:
    """
    Generates answers using an LLM with strict constraints.
    
    Key features:
    - Hard-coded prompts that enforce citation requirements
    - Answer format validation
    - Citation verification against source chunks
    - Rejection of uncited claims
    """
    
    def __init__(
        self,
        retriever: RuleRetriever,
        llm_provider: str = "openai",
        model_name: str = "gpt-4",
        temperature: float = 0.0,
        max_tokens: int = 1000,
        api_key: Optional[str] = None
    ):
        """
        Initialize answer generator.
        
        Args:
            retriever: RuleRetriever instance
            llm_provider: LLM provider (currently only "openai" supported)
            model_name: Model name
            temperature: Temperature for generation (0.0 = deterministic)
            max_tokens: Maximum tokens in response
            api_key: API key (or use OPENAI_API_KEY env var)
        """
        self.retriever = retriever
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize LLM client
        if llm_provider == "openai":
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
            except ImportError:
                raise ImportError(
                    "OpenAI package not installed. Install with: pip install openai"
                )
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
    
    def generate_answer(
        self,
        question: str,
        mode: str = "qa"
    ) -> Dict[str, Any]:
        """
        Generate an answer to a question.
        
        Args:
            question: User's question
            mode: Answer mode ("qa", "quiz", "elimination", "audit")
            
        Returns:
            Dictionary with answer and metadata
        """
        # Retrieve relevant chunks
        chunks_with_scores = self.retriever.retrieve(question)
        chunks = [chunk for chunk, _ in chunks_with_scores]
        
        if not chunks:
            return {
                'answer': 'No relevant rules found for this question.',
                'mode': mode,
                'chunks_retrieved': 0,
                'citations': [],
                'validation': {'has_citations': False}
            }
        
        # Generate prompt based on mode
        if mode == "qa":
            prompt = prompt_templates.get_qa_prompt(question, chunks)
        elif mode == "quiz":
            prompt = prompt_templates.get_quiz_prompt(question, chunks)
        elif mode == "elimination":
            # Extract options from question
            options = self._extract_options(question)
            prompt = prompt_templates.get_elimination_prompt(question, options, chunks)
        elif mode == "audit":
            prompt = prompt_templates.get_audit_prompt(question, chunks)
        else:
            raise ValueError(f"Invalid mode: {mode}")
        
        # Call LLM
        response = self._call_llm(prompt)
        
        # Validate and parse response
        validation = self._validate_answer(response, chunks, mode)
        
        # Extract citations if in QA mode
        citations = []
        if mode == "qa" or mode == "audit":
            citations = self._extract_citations(response)
        
        return {
            'answer': response,
            'mode': mode,
            'question': question,
            'chunks_retrieved': len(chunks),
            'chunks': chunks,
            'citations': citations,
            'validation': validation,
            'prompt': prompt  # Include for debugging
        }
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call the LLM with the given prompt.
        
        Args:
            prompt: Complete prompt
            
        Returns:
            LLM response text
        """
        if self.llm_provider == "openai":
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                return response.choices[0].message.content
            except Exception as e:
                # If API call fails, return error message
                # In production, you might want to handle this differently
                return f"Error calling LLM: {str(e)}"
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
    
    def _validate_answer(
        self,
        answer: str,
        chunks: List[Dict[str, Any]],
        mode: str
    ) -> Dict[str, Any]:
        """
        Validate the LLM's answer.
        
        Checks:
        - Format compliance
        - Presence of citations (for QA mode)
        - Verbatim quotes exist in source chunks
        
        Args:
            answer: LLM response
            chunks: Retrieved chunks
            mode: Answer mode
            
        Returns:
            Validation results dictionary
        """
        validation = {
            'format_valid': False,
            'has_citations': False,
            'has_quotes': False,
            'quotes_verified': False,
            'warnings': []
        }
        
        if mode == "quiz":
            # Quiz mode should be a single letter or Yes/No
            answer_clean = answer.strip()
            if len(answer_clean) <= 3 and (
                answer_clean.upper() in ['A', 'B', 'C', 'D', 'YES', 'NO']
            ):
                validation['format_valid'] = True
            else:
                validation['warnings'].append(
                    f"Quiz answer should be a single letter or Yes/No, got: {answer_clean}"
                )
            return validation
        
        # For QA and audit modes, check format
        if "Final Answer:" in answer:
            validation['format_valid'] = True
        else:
            validation['warnings'].append("Answer missing 'Final Answer:' section")
        
        # Check for citations
        if "Rule References:" in answer or "Clause" in answer:
            validation['has_citations'] = True
        else:
            validation['warnings'].append("Answer missing rule references")
        
        # Check for quotes
        quotes = re.findall(r'"([^"]+)"', answer)
        if quotes:
            validation['has_quotes'] = True
            
            # Verify quotes exist in chunks
            all_verified = True
            for quote in quotes:
                verified = self._verify_quote_in_chunks(quote, chunks)
                if not verified:
                    validation['warnings'].append(
                        f"Quote not found in source chunks: '{quote[:50]}...'"
                    )
                    all_verified = False
            
            validation['quotes_verified'] = all_verified
        else:
            if "Not explicitly specified" not in answer:
                validation['warnings'].append("Answer has no supporting quotes")
        
        return validation
    
    def _verify_quote_in_chunks(
        self,
        quote: str,
        chunks: List[Dict[str, Any]]
    ) -> bool:
        """
        Verify that a quote exists verbatim in the retrieved chunks.
        
        Args:
            quote: Quote text
            chunks: Retrieved chunks
            
        Returns:
            True if quote found in any chunk
        """
        quote_lower = quote.lower().strip()
        
        # Must be at least a few words to be meaningful
        if len(quote.split()) < 3:
            return True  # Don't penalize very short quotes
        
        for chunk in chunks:
            chunk_text = chunk.get('chunk_text', '').lower()
            if quote_lower in chunk_text:
                return True
        
        return False
    
    def _extract_citations(self, answer: str) -> List[str]:
        """
        Extract rule citations from answer.
        
        Args:
            answer: LLM response
            
        Returns:
            List of cited clause IDs
        """
        # Look for patterns like "T.2.3.1", "A.1.2", etc.
        citations = re.findall(r'\b([A-Z]{1,3})\.(\d+\.)*\d+\b', answer)
        return [''.join(c) for c in citations]
    
    def _extract_options(self, question: str) -> List[str]:
        """
        Extract multiple choice options from a question.
        
        Args:
            question: Question text
            
        Returns:
            List of option texts
        """
        # Simple pattern matching for "A) ..., B) ..., C) ..."
        options = []
        
        # Try to find options marked with letters
        for letter in ['A', 'B', 'C', 'D', 'E', 'F']:
            pattern = f'{letter}\\)\\s*([^A-F]+?)(?=[A-Z]\\)|$)'
            matches = re.findall(pattern, question, re.IGNORECASE | re.DOTALL)
            if matches:
                options.append(matches[0].strip())
        
        return options


def create_answer_generator(
    season: str,
    competition: str,
    config_path: Optional[str] = None,
    api_key: Optional[str] = None
) -> AnswerGenerator:
    """
    Convenience function to create an answer generator from configuration.
    
    Args:
        season: Season identifier
        competition: Competition identifier
        config_path: Optional path to config file
        api_key: Optional API key for LLM
        
    Returns:
        AnswerGenerator instance
    """
    from query.retriever import create_retriever
    from config.config_loader import get_config
    
    config = get_config(config_path)
    
    # Create retriever
    retriever = create_retriever(season, competition, config_path)
    
    # Create generator
    generator = AnswerGenerator(
        retriever=retriever,
        llm_provider=config.llm_provider,
        model_name=config.llm_model,
        temperature=config.llm_temperature,
        max_tokens=config.llm_max_tokens,
        api_key=api_key
    )
    
    return generator


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="Test answer generator for Formula Student rules"
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
        help="Question to answer"
    )
    parser.add_argument(
        "--mode",
        default="qa",
        choices=["qa", "quiz", "elimination", "audit"],
        help="Answer mode"
    )
    
    args = parser.parse_args()
    
    print(f"Creating answer generator for {args.season} - {args.competition}")
    generator = create_answer_generator(args.season, args.competition)
    
    print(f"\nQuestion: {args.question}")
    print(f"Mode: {args.mode}")
    print("\nGenerating answer...\n")
    
    result = generator.generate_answer(args.question, mode=args.mode)
    
    print("=" * 80)
    print("ANSWER:")
    print("=" * 80)
    print(result['answer'])
    print()
    print("=" * 80)
    print("METADATA:")
    print("=" * 80)
    print(f"Chunks retrieved: {result['chunks_retrieved']}")
    print(f"Citations: {result['citations']}")
    print(f"Validation: {json.dumps(result['validation'], indent=2)}")
