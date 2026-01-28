"""
Elimination Mode for Formula Student Rules.

Analyzes multiple choice options and eliminates incorrect ones.
Provides detailed reasoning for each option.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from query.answer_generator import AnswerGenerator, create_answer_generator


class EliminationMode:
    """
    Elimination mode handler for MCQ questions.
    
    Analyzes each option individually and determines if it can be
    eliminated based on the rules.
    """
    
    def __init__(self, generator: AnswerGenerator):
        """
        Initialize elimination mode.
        
        Args:
            generator: AnswerGenerator instance
        """
        self.generator = generator
    
    def analyze_options(
        self,
        question: str,
        options: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze multiple choice options.
        
        Args:
            question: Question text (without options)
            options: List of option texts
            
        Returns:
            Dictionary with analysis for each option
        """
        # Build full question with options
        full_question = question + "\n\nOptions:\n"
        for i, opt in enumerate(options):
            full_question += f"{chr(65+i)}) {opt}\n"
        
        # Generate answer using elimination mode
        result = self.generator.generate_answer(full_question, mode="elimination")
        
        # Parse the response to extract option analysis
        analysis = self._parse_analysis(result['answer'], options)
        
        return {
            'question': question,
            'options': options,
            'analysis': analysis,
            'raw_response': result['answer'],
            'chunks_retrieved': result['chunks_retrieved'],
            'validation': result['validation']
        }
    
    def _parse_analysis(
        self,
        response: str,
        options: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Parse the LLM's option analysis.
        
        Args:
            response: LLM response
            options: Original options
            
        Returns:
            List of analysis dictionaries, one per option
        """
        analyses = []
        
        # Simple parsing - look for patterns like "A)" or "Option A"
        for i, option_text in enumerate(options):
            letter = chr(65 + i)
            
            # Try to find the section for this option
            # This is a simple heuristic; in production you might want more robust parsing
            pattern_start = f"{letter})"
            
            # Find the section in the response
            if pattern_start in response:
                start_idx = response.index(pattern_start)
                # Find the end (next option or end of text)
                end_idx = len(response)
                for next_letter in range(i + 1, len(options)):
                    next_pattern = f"{chr(65 + next_letter)})"
                    if next_pattern in response[start_idx + 1:]:
                        end_idx = start_idx + response[start_idx:].index(next_pattern)
                        break
                
                section = response[start_idx:end_idx]
                
                # Determine status
                status = "UNCERTAIN"
                if "CORRECT" in section.upper():
                    status = "CORRECT"
                elif "INCORRECT" in section.upper():
                    status = "INCORRECT"
                
                analyses.append({
                    'option': letter,
                    'text': option_text,
                    'status': status,
                    'reasoning': section.strip()
                })
            else:
                # If we can't find analysis, mark as uncertain
                analyses.append({
                    'option': letter,
                    'text': option_text,
                    'status': 'UNCERTAIN',
                    'reasoning': 'No analysis found'
                })
        
        return analyses
    
    def get_recommendation(self, analysis: Dict[str, Any]) -> str:
        """
        Get recommendation based on option analysis.
        
        Args:
            analysis: Analysis dictionary from analyze_options
            
        Returns:
            Recommendation string
        """
        options_analysis = analysis['analysis']
        
        correct_options = [a for a in options_analysis if a['status'] == 'CORRECT']
        incorrect_options = [a for a in options_analysis if a['status'] == 'INCORRECT']
        uncertain_options = [a for a in options_analysis if a['status'] == 'UNCERTAIN']
        
        if len(correct_options) == 1:
            return f"Choose {correct_options[0]['option']}: Clearly supported by rules"
        elif len(correct_options) > 1:
            letters = [a['option'] for a in correct_options]
            return f"Multiple options appear correct: {', '.join(letters)}. Review carefully."
        elif len(uncertain_options) > 0 and len(incorrect_options) < len(options_analysis):
            # Some options eliminated, but no clear correct answer
            remaining = [a['option'] for a in uncertain_options]
            eliminated = [a['option'] for a in incorrect_options]
            return f"Eliminated: {', '.join(eliminated)}. Consider: {', '.join(remaining)}"
        else:
            return "Unable to determine correct answer from rules. Choose most conservative option."


def run_elimination_mode(
    season: str,
    competition: str,
    question: str,
    options: List[str]
) -> Dict[str, Any]:
    """
    Convenience function to run elimination mode.
    
    Args:
        season: Season identifier
        competition: Competition identifier
        question: Question text
        options: List of option texts
        
    Returns:
        Analysis dictionary
    """
    generator = create_answer_generator(season, competition)
    elimination = EliminationMode(generator)
    analysis = elimination.analyze_options(question, options)
    
    # Add recommendation
    recommendation = elimination.get_recommendation(analysis)
    analysis['recommendation'] = recommendation
    
    return analysis


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="Analyze MCQ options for Formula Student questions"
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
        help="Question text"
    )
    parser.add_argument(
        "--options",
        required=True,
        nargs='+',
        help="Option texts (e.g., --options 'Option A' 'Option B' 'Option C')"
    )
    
    args = parser.parse_args()
    
    analysis = run_elimination_mode(
        args.season,
        args.competition,
        args.question,
        args.options
    )
    
    print("\n" + "=" * 80)
    print("OPTION ELIMINATION ANALYSIS")
    print("=" * 80)
    print(f"\nQuestion: {analysis['question']}\n")
    
    for opt_analysis in analysis['analysis']:
        print(f"{opt_analysis['option']}) {opt_analysis['text']}")
        print(f"   Status: {opt_analysis['status']}")
        print(f"   Reasoning: {opt_analysis['reasoning'][:200]}...")
        print()
    
    print("=" * 80)
    print("RECOMMENDATION:")
    print("=" * 80)
    print(analysis['recommendation'])
    print()
