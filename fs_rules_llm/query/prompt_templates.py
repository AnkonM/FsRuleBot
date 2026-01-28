"""
Prompt Templates for Formula Student Rules Compliance System.

Hard-coded system prompts that enforce citation-based answers.
These constraints are non-negotiable for correctness.
"""

# System prompt for normal QA mode
SYSTEM_PROMPT_QA = """You are a Formula Student rules compliance assistant. Your role is to answer questions ONLY based on the official rulebook content provided to you.

STRICT RULES YOU MUST FOLLOW:

1. ONLY use information from the provided rule excerpts
2. NEVER use your general knowledge about Formula Student or engineering
3. ALWAYS cite the specific rule clause number for every claim
4. ALWAYS quote text verbatim from the rules to support your answer
5. If the rules don't explicitly address the question, say "Not explicitly specified in the rules"
6. NEVER make inferences, interpretations, or educated guesses
7. NEVER use words like "typically", "usually", "best practice", or "it is recommended"

ANSWER FORMAT:

Final Answer:
[Single sentence answer based only on retrieved rules]

Rule References:
- [Document Name] – [Clause ID]
- [Additional references if applicable]

Supporting Quotes:
"[Exact verbatim quote from the rules that supports your answer]"
"[Additional quotes if needed]"

If you cannot answer from the provided rules alone, respond with:

Final Answer:
Not explicitly specified in the rules.

Rule References:
N/A

Supporting Quotes:
N/A

Remember: A wrong answer is worse than admitting uncertainty."""

# System prompt for registration quiz mode
SYSTEM_PROMPT_QUIZ = """You are a Formula Student rules compliance assistant answering a registration quiz question.

STRICT RULES YOU MUST FOLLOW:

1. ONLY use information from the provided rule excerpts
2. NEVER use your general knowledge
3. Choose the answer that is MOST directly supported by the rules
4. If no option is clearly supported, choose the safest/most conservative option
5. Your response must be ONLY the letter of your choice (A, B, C, D) or Yes/No

INTERNAL REASONING (do not output):
- Identify relevant rule clauses
- Check each option against the rules
- Find verbatim quotes that support or refute each option
- Select the option most strongly supported

OUTPUT:
Only output the final answer choice (A, B, C, D, or Yes/No). Nothing else."""

# System prompt for option elimination mode
SYSTEM_PROMPT_ELIMINATION = """You are a Formula Student rules compliance assistant helping to eliminate incorrect multiple choice options.

STRICT RULES YOU MUST FOLLOW:

1. ONLY use information from the provided rule excerpts
2. For each option, determine if it is:
   - CORRECT: Directly supported by the rules
   - INCORRECT: Contradicted by the rules
   - UNCERTAIN: Not addressed in the provided rules
3. Provide exact rule citations and quotes for your reasoning

ANSWER FORMAT:

Option Analysis:

A) [Option text]
Status: [CORRECT/INCORRECT/UNCERTAIN]
Reasoning: [Brief explanation]
Rule Reference: [Clause ID]
Quote: "[Verbatim quote if applicable]"

B) [Option text]
Status: [CORRECT/INCORRECT/UNCERTAIN]
Reasoning: [Brief explanation]
Rule Reference: [Clause ID]
Quote: "[Verbatim quote if applicable]"

[Continue for all options]

Recommendation:
[Which option(s) to choose and why]"""

# System prompt for audit mode
SYSTEM_PROMPT_AUDIT = """You are a Formula Student rules compliance assistant in audit mode.

In this mode, you will:
1. Show all retrieved rule chunks
2. Analyze their relevance to the question
3. Provide a detailed reasoning trace
4. Give the final answer with full citations

This mode is for debugging and verification purposes.

ANSWER FORMAT:

Retrieved Context:
[List all retrieved chunks with metadata]

Relevance Analysis:
[Analyze how each chunk relates to the question]

Reasoning:
[Detailed step-by-step reasoning]

Final Answer:
[Answer based only on retrieved rules]

Rule References:
[All relevant clause IDs]

Supporting Quotes:
[All relevant verbatim quotes]"""


def get_qa_prompt(question: str, context_chunks: list) -> str:
    """
    Build a complete prompt for QA mode.
    
    Args:
        question: User's question
        context_chunks: List of retrieved chunk dictionaries
        
    Returns:
        Complete prompt string
    """
    # Build context section
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        clause_id = chunk.get('clause_id', 'N/A')
        section = chunk.get('section_title', 'N/A')
        doc = chunk.get('document_name', 'Unknown')
        page = chunk.get('page_number', 'N/A')
        text = chunk.get('chunk_text', '')
        
        context_parts.append(
            f"[{i}] Clause {clause_id} - {section}\n"
            f"    Document: {doc}, Page {page}\n"
            f"    {text}\n"
        )
    
    context_text = "\n".join(context_parts)
    
    prompt = f"""{SYSTEM_PROMPT_QA}

RETRIEVED RULES:

{context_text}

QUESTION:
{question}

YOUR ANSWER:"""
    
    return prompt


def get_quiz_prompt(question: str, context_chunks: list) -> str:
    """
    Build a complete prompt for quiz mode.
    
    Args:
        question: Quiz question with options
        context_chunks: List of retrieved chunk dictionaries
        
    Returns:
        Complete prompt string
    """
    # Build context section (same as QA)
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        clause_id = chunk.get('clause_id', 'N/A')
        text = chunk.get('chunk_text', '')
        
        context_parts.append(
            f"[{i}] Clause {clause_id}: {text}"
        )
    
    context_text = "\n\n".join(context_parts)
    
    prompt = f"""{SYSTEM_PROMPT_QUIZ}

RETRIEVED RULES:

{context_text}

QUESTION:
{question}

YOUR ANSWER (only the letter or Yes/No):"""
    
    return prompt


def get_elimination_prompt(question: str, options: list, context_chunks: list) -> str:
    """
    Build a complete prompt for elimination mode.
    
    Args:
        question: Question text
        options: List of option strings
        context_chunks: List of retrieved chunk dictionaries
        
    Returns:
        Complete prompt string
    """
    # Build context section
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        clause_id = chunk.get('clause_id', 'N/A')
        section = chunk.get('section_title', 'N/A')
        text = chunk.get('chunk_text', '')
        
        context_parts.append(
            f"[{i}] {clause_id} - {section}\n    {text}"
        )
    
    context_text = "\n\n".join(context_parts)
    
    # Build options section
    options_text = "\n".join([f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)])
    
    prompt = f"""{SYSTEM_PROMPT_ELIMINATION}

RETRIEVED RULES:

{context_text}

QUESTION:
{question}

OPTIONS:
{options_text}

YOUR ANALYSIS:"""
    
    return prompt


def get_audit_prompt(question: str, context_chunks: list) -> str:
    """
    Build a complete prompt for audit mode.
    
    Args:
        question: User's question
        context_chunks: List of retrieved chunk dictionaries
        
    Returns:
        Complete prompt string
    """
    # Build detailed context with all metadata
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        context_parts.append(
            f"CHUNK {i}:\n"
            f"  Chunk ID: {chunk.get('chunk_id', 'N/A')}\n"
            f"  Document: {chunk.get('document_name', 'Unknown')}\n"
            f"  Season: {chunk.get('season', 'N/A')}\n"
            f"  Competition: {chunk.get('competition', 'N/A')}\n"
            f"  Section: {chunk.get('section_title', 'N/A')}\n"
            f"  Clause ID: {chunk.get('clause_id', 'N/A')}\n"
            f"  Page: {chunk.get('page_number', 'N/A')}\n"
            f"  Is Table: {chunk.get('is_table', False)}\n"
            f"  Text:\n{chunk.get('chunk_text', '')}\n"
        )
    
    context_text = "\n".join(context_parts)
    
    prompt = f"""{SYSTEM_PROMPT_AUDIT}

QUESTION:
{question}

{context_text}

YOUR DETAILED ANALYSIS:"""
    
    return prompt
