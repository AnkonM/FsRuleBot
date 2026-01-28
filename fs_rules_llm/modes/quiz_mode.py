"""
Registration Quiz Mode for Formula Student Rules.

Handles registration quiz questions with simple A/B/C/D or Yes/No output.
Logs full reasoning and citations internally.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from query.answer_generator import AnswerGenerator, create_answer_generator


class QuizMode:
    """
    Quiz mode handler for registration questions.
    
    Outputs only the final choice (A/B/C/D or Yes/No).
    Full reasoning and citations are logged internally for audit.
    """
    
    def __init__(self, generator: AnswerGenerator, log_file: Optional[str] = None):
        """
        Initialize quiz mode.
        
        Args:
            generator: AnswerGenerator instance
            log_file: Optional path to log detailed reasoning
        """
        self.generator = generator
        self.log_file = log_file
    
    def answer_quiz(
        self,
        question: str,
        choices: Optional[str] = None
    ) -> str:
        """
        Answer a quiz question.
        
        Args:
            question: Quiz question text (may include choices)
            choices: Optional comma-separated list of valid choices (e.g., "A,B,C,D")
            
        Returns:
            Single letter choice or Yes/No
        """
        # Generate answer using quiz mode
        result = self.generator.generate_answer(question, mode="quiz")
        
        # Log full reasoning if log file specified
        if self.log_file:
            self._log_reasoning(question, result)
        
        # Extract and validate final answer
        answer = result['answer'].strip().upper()
        
        # Validate against expected choices if provided
        if choices:
            valid_choices = [c.strip().upper() for c in choices.split(',')]
            if answer not in valid_choices:
                # Try to extract a valid choice from the answer
                for choice in valid_choices:
                    if choice in answer:
                        answer = choice
                        break
                else:
                    # If still not valid, log warning
                    if self.log_file:
                        with open(self.log_file, 'a') as f:
                            f.write(f"\nWARNING: Invalid choice '{answer}', expected one of {valid_choices}\n")
        
        return answer
    
    def _log_reasoning(self, question: str, result: Dict[str, Any]):
        """
        Log detailed reasoning to file.
        
        Args:
            question: Original question
            result: Full result dictionary from answer generator
        """
        log_entry = {
            'question': question,
            'answer': result['answer'],
            'chunks_retrieved': result['chunks_retrieved'],
            'validation': result['validation'],
            'chunks': [
                {
                    'clause_id': chunk.get('clause_id'),
                    'section': chunk.get('section_title'),
                    'text': chunk.get('chunk_text')[:200] + '...'  # Truncate for readability
                }
                for chunk in result.get('chunks', [])
            ]
        }
        
        with open(self.log_file, 'a') as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(json.dumps(log_entry, indent=2))
            f.write("\n")


def run_quiz_mode(
    season: str,
    competition: str,
    question: str,
    choices: Optional[str] = None,
    log_file: Optional[str] = None
) -> str:
    """
    Convenience function to run quiz mode.
    
    Args:
        season: Season identifier
        competition: Competition identifier
        question: Quiz question
        choices: Valid choices (optional)
        log_file: Log file path (optional)
        
    Returns:
        Answer choice
    """
    generator = create_answer_generator(season, competition)
    quiz = QuizMode(generator, log_file)
    return quiz.answer_quiz(question, choices)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Answer Formula Student registration quiz questions"
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
        help="Quiz question"
    )
    parser.add_argument(
        "--choices",
        help="Valid choices (e.g., 'A,B,C,D' or 'Yes,No')"
    )
    parser.add_argument(
        "--log",
        help="Log file for detailed reasoning"
    )
    
    args = parser.parse_args()
    
    answer = run_quiz_mode(
        args.season,
        args.competition,
        args.question,
        args.choices,
        args.log
    )
    
    # Output only the answer (as required by quiz mode)
    print(answer)
