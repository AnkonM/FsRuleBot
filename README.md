# Formula Student Rules Compliance and Quiz-Answering System

## System Philosophy

This is a **correctness-critical** retrieval-augmented LLM system designed to answer Formula Student registration quiz questions using **only official documents as ground truth**.

### Core Principles

1. **Accuracy over Completeness**: A wrong answer is worse than responding with "not specified in the rules"
2. **No Hallucination**: Never answer from general LLM knowledge or engineering intuition
3. **Exact Citations**: Every answer must include rule references and verbatim quotes
4. **Version Isolation**: Never mix rules from different seasons or competitions
5. **Fail Loudly**: Reject responses that lack citations or contain uncited claims

### Mental Model

This system behaves like a **Formula Student scrutineer building an automated compliance checker**:
- Accuracy is more important than completeness
- Completeness is more important than elegance
- When in doubt, cite the exact rule or admit the limitation

## Architecture

### Retrieval-Augmented Generation (RAG) Pipeline

```
PDF Documents → Chunking → Vector Embeddings → Filtered Retrieval → LLM with Citations
```

### Key Components

1. **Ingestion Pipeline**: Parses PDFs with layout awareness, preserves structure, validates chunks
2. **Vector Storage**: FAISS-based local storage with strict season/competition filtering
3. **Retrieval**: Top 5-8 chunks with metadata filters and sanity checks
4. **LLM Prompting**: Hard-coded constraints forcing citation-based answers only
5. **Operating Modes**: Normal QA, Registration Quiz, Option Elimination, Audit

## Project Structure

```
fs_rules_llm/
├── data/
│   ├── raw/<season>/<competition>/         # Original PDF rulebooks
│   ├── processed/                           # Validated chunks with metadata
│   └── indices/                             # FAISS vector indices per season
│
├── ingestion/
│   ├── pdf_parser.py                        # Layout-aware PDF parsing
│   ├── chunker.py                           # Intelligent chunking (150-400 words)
│   └── validate_chunks.py                   # Chunk validation and rejection
│
├── embeddings/
│   ├── embed_rules.py                       # Embedding generation for chunks
│   └── vector_store.py                      # FAISS index management
│
├── query/
│   ├── retriever.py                         # Season/competition-filtered retrieval
│   ├── prompt_templates.py                  # Hard-coded system prompts
│   └── answer_generator.py                  # LLM interface with validation
│
├── modes/
│   ├── quiz_mode.py                         # Registration quiz (A/B/C/D output)
│   ├── elimination_mode.py                  # MCQ option elimination
│   └── audit_mode.py                        # Expose retrieved context
│
├── config/
│   └── seasons.yaml                         # Season/competition definitions
│
├── examples/
│   └── verified_questions.md                # Golden test cases
│
├── tests/
│   ├── test_chunking.py
│   ├── test_retrieval.py
│   └── test_citations.py
│
├── main.py                                   # Entry point
├── requirements.txt
└── README.md
```

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Ingest Documents

```bash
python -m fs_rules_llm.ingestion.pdf_parser \
    --input data/raw/2024/FSAE \
    --season 2024 \
    --competition FSAE
```

### 2. Build Vector Index

```bash
python -m fs_rules_llm.embeddings.embed_rules \
    --season 2024 \
    --competition FSAE
```

### 3. Query the System

**Normal QA Mode:**
```bash
python main.py --mode qa \
    --season 2024 \
    --competition FSAE \
    --question "What is the minimum wheelbase requirement?"
```

**Registration Quiz Mode:**
```bash
python main.py --mode quiz \
    --season 2024 \
    --competition FSAE \
    --question "Is a brake light required? A) Yes B) No" \
    --choices "A,B"
```

**Audit Mode (Debug):**
```bash
python main.py --mode audit \
    --season 2024 \
    --competition FSAE \
    --question "What are the roll hoop requirements?"
```

## Answer Format

### Normal Mode Output

```
Final Answer:
The minimum wheelbase is 1525 mm.

Rule References:
- FSAE 2024 Rules – T.2.3.1

Supporting Quotes:
"The wheelbase, measured as per T.1.1, must be at least 1525 mm."
```

### Quiz Mode Output

```
A
```
(Full reasoning and citations logged internally)

## Operating Rules

### What the System WILL Do

✅ Answer only from retrieved rulebook content  
✅ Provide exact rule citations and verbatim quotes  
✅ Support multiple seasons without mixing rules  
✅ Say "Not explicitly specified in the rules" when applicable  
✅ Reject uncited or unsupported claims  

### What the System WILL NOT Do

❌ Answer from general engineering knowledge  
❌ Make inferences or interpretations  
❌ Guess or assume missing information  
❌ Mix rule versions from different seasons  
❌ Provide answers without citations  

## Chunk Metadata

Each chunk includes:
- `document_name`: Source PDF filename
- `season`: e.g., "2024"
- `competition`: e.g., "FSAE", "Formula Student"
- `section_title`: e.g., "Technical Rules - Chassis"
- `clause_id`: e.g., "T.2.3.1" (if present)
- `chunk_text`: 150-400 words of rule text
- `page_number`: Source page reference

## Versioning

- Each season has a **separate vector index**
- Season selection is **explicit** (no auto-fallback)
- Updating documents **never affects existing seasons**
- Indices are immutable after creation

## Testing and Verification

### Unit Tests
```bash
pytest tests/
```

### Manual Verification
1. Check that quoted text exists verbatim in source
2. Verify rule numbers match actual clauses
3. Confirm no hallucination or inference
4. Validate answer format compliance

### Golden Test Cases

See `examples/verified_questions.md` for manually verified correct answers used as regression tests.

## Development Principles

1. **Explicit over Clever**: Prefer readable, defensive code
2. **Comment Reasoning**: Explain assumptions and design choices
3. **Fail Loudly**: Assert violations, don't silently continue
4. **No Silent Mixing**: Never auto-select or merge rule versions
5. **Document Ambiguity**: Flag unclear requirements immediately

## License

MIT License - See LICENSE file for details

## Contributing

This is a compliance-critical system. All contributions must:
1. Maintain strict citation requirements
2. Include tests with verified correct answers
3. Never relax accuracy constraints for convenience
4. Document all assumptions and limitations