"""
Main entry point for Formula Student Rules Compliance System.

Provides a unified CLI interface for all operating modes.
"""

import argparse
import sys
import os
from pathlib import Path

# Add fs_rules_llm to path
sys.path.insert(0, str(Path(__file__).parent))

from fs_rules_llm.config.config_loader import get_config
from fs_rules_llm.query.answer_generator import create_answer_generator
from fs_rules_llm.modes.quiz_mode import QuizMode
from fs_rules_llm.modes.elimination_mode import EliminationMode
from fs_rules_llm.modes.audit_mode import AuditMode


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Formula Student Rules Compliance and Quiz-Answering System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Normal QA mode
  python main.py --mode qa --season 2024 --competition FSAE \\
      --question "What is the minimum wheelbase requirement?"
  
  # Registration quiz mode
  python main.py --mode quiz --season 2024 --competition FSAE \\
      --question "Is a brake light required? A) Yes B) No" --choices A,B
  
  # Elimination mode
  python main.py --mode elimination --season 2024 --competition FSAE \\
      --question "What is the minimum brake disc diameter?" \\
      --options "200mm" "250mm" "300mm"
  
  # Audit mode (debugging)
  python main.py --mode audit --season 2024 --competition FSAE \\
      --question "What are the roll hoop requirements?"
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--mode",
        required=True,
        choices=["qa", "quiz", "elimination", "audit"],
        help="Operating mode"
    )
    parser.add_argument(
        "--season",
        required=True,
        help="Season identifier (e.g., 2024)"
    )
    parser.add_argument(
        "--competition",
        required=True,
        help="Competition identifier (e.g., FSAE, FS, FSG)"
    )
    parser.add_argument(
        "--question",
        required=True,
        help="Question to answer"
    )
    
    # Mode-specific arguments
    parser.add_argument(
        "--choices",
        help="Valid choices for quiz mode (e.g., 'A,B,C,D')"
    )
    parser.add_argument(
        "--options",
        nargs='+',
        help="Options for elimination mode"
    )
    parser.add_argument(
        "--log",
        help="Log file for quiz mode reasoning"
    )
    parser.add_argument(
        "--output",
        help="Output file for audit mode report (JSON)"
    )
    
    # Configuration
    parser.add_argument(
        "--config",
        help="Path to configuration file (default: auto-detect)"
    )
    
    args = parser.parse_args()
    
    # Validate API key is set for LLM
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set it with: export OPENAI_API_KEY=your-key-here")
        sys.exit(1)
    
    try:
        # Create answer generator
        print(f"Initializing {args.mode} mode for {args.season} - {args.competition}...")
        generator = create_answer_generator(
            args.season,
            args.competition,
            config_path=args.config
        )
        
        # Run appropriate mode
        if args.mode == "qa":
            run_qa_mode(generator, args.question)
        
        elif args.mode == "quiz":
            run_quiz_mode_cli(generator, args.question, args.choices, args.log)
        
        elif args.mode == "elimination":
            if not args.options:
                print("ERROR: --options required for elimination mode")
                sys.exit(1)
            run_elimination_mode_cli(generator, args.question, args.options)
        
        elif args.mode == "audit":
            run_audit_mode_cli(generator, args.question, args.output)
    
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("\nMake sure you have built the index for this season/competition.")
        print("See README.md for instructions on building indices.")
        sys.exit(1)
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_qa_mode(generator, question):
    """Run normal QA mode."""
    print(f"\nQuestion: {question}\n")
    print("Generating answer...\n")
    
    result = generator.generate_answer(question, mode="qa")
    
    print("=" * 80)
    print(result['answer'])
    print("=" * 80)
    
    # Show validation warnings if any
    if result['validation'].get('warnings'):
        print("\nValidation Warnings:")
        for warning in result['validation']['warnings']:
            print(f"  ⚠ {warning}")


def run_quiz_mode_cli(generator, question, choices, log_file):
    """Run quiz mode from CLI."""
    quiz = QuizMode(generator, log_file)
    answer = quiz.answer_quiz(question, choices)
    
    # Output only the answer (as required by quiz mode)
    print(answer)
    
    if log_file:
        print(f"\nDetailed reasoning logged to: {log_file}", file=sys.stderr)


def run_elimination_mode_cli(generator, question, options):
    """Run elimination mode from CLI."""
    elimination = EliminationMode(generator)
    analysis = elimination.analyze_options(question, options)
    recommendation = elimination.get_recommendation(analysis)
    
    print("\n" + "=" * 80)
    print("OPTION ELIMINATION ANALYSIS")
    print("=" * 80)
    print(f"\nQuestion: {question}\n")
    
    for opt_analysis in analysis['analysis']:
        print(f"{opt_analysis['option']}) {opt_analysis['text']}")
        print(f"   Status: {opt_analysis['status']}")
        # Print first 200 chars of reasoning
        reasoning = opt_analysis['reasoning']
        if len(reasoning) > 200:
            reasoning = reasoning[:200] + "..."
        print(f"   Reasoning: {reasoning}")
        print()
    
    print("=" * 80)
    print("RECOMMENDATION:")
    print("=" * 80)
    print(recommendation)
    print()


def run_audit_mode_cli(generator, question, output_file):
    """Run audit mode from CLI."""
    import json
    
    audit = AuditMode(generator)
    report = audit.audit_question(question)
    
    # Print formatted report
    audit.print_audit_report(report)
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    main()
