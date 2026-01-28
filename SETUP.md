# Setup Guide for Formula Student Rules Compliance System

## Prerequisites

- Python 3.8 or higher
- pip package manager
- OpenAI API key (or compatible LLM API)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/AnkonM/FsRuleBot.git
cd FsRuleBot
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up API Key

Create a `.env` file in the root directory:

```bash
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

Or export it directly:

```bash
export OPENAI_API_KEY=your-api-key-here
```

### 5. Prepare Data Directory Structure

The directories are already created, but verify:

```bash
ls -la fs_rules_llm/data/
# Should show: raw/ processed/ indices/
```

## Data Ingestion Workflow

### Step 1: Add PDF Documents

Place your Formula Student rulebooks in the appropriate directory:

```bash
fs_rules_llm/data/raw/2024/FSAE/FSAE_Rules_2024.pdf
fs_rules_llm/data/raw/2024/FS/FS_Rules_2024.pdf
```

### Step 2: Parse PDFs

```bash
python -m fs_rules_llm.ingestion.pdf_parser \
    --input fs_rules_llm/data/raw/2024/FSAE/FSAE_Rules_2024.pdf \
    --season 2024 \
    --competition FSAE \
    --output fs_rules_llm/data/processed/2024_FSAE_sections.json
```

### Step 3: Chunk Sections

```bash
python -m fs_rules_llm.ingestion.chunker \
    --input fs_rules_llm/data/processed/2024_FSAE_sections.json \
    --output fs_rules_llm/data/processed/2024_FSAE_chunks.json \
    --min-words 150 \
    --max-words 400 \
    --overlap 50
```

### Step 4: Validate Chunks

```bash
python -m fs_rules_llm.ingestion.validate_chunks \
    --input fs_rules_llm/data/processed/2024_FSAE_chunks.json \
    --output fs_rules_llm/data/processed/2024_FSAE_chunks_validated.json \
    --errors fs_rules_llm/data/processed/2024_FSAE_errors.json \
    --strict
```

### Step 5: Generate Embeddings

```bash
python -m fs_rules_llm.embeddings.embed_rules \
    --input fs_rules_llm/data/processed/2024_FSAE_chunks_validated.json \
    --output fs_rules_llm/data/processed/2024_FSAE_embeddings.npy
```

### Step 6: Build Vector Index

```bash
python -m fs_rules_llm.embeddings.vector_store \
    --chunks fs_rules_llm/data/processed/2024_FSAE_chunks_validated.json \
    --embeddings fs_rules_llm/data/processed/2024_FSAE_embeddings.npy \
    --output fs_rules_llm/data/indices/2024_FSAE \
    --season 2024 \
    --competition FSAE
```

## Usage Examples

### Normal QA Mode

```bash
python main.py \
    --mode qa \
    --season 2024 \
    --competition FSAE \
    --question "What is the minimum wheelbase requirement?"
```

### Registration Quiz Mode

```bash
python main.py \
    --mode quiz \
    --season 2024 \
    --competition FSAE \
    --question "Is a brake light required? A) Yes B) No" \
    --choices A,B \
    --log quiz_log.txt
```

### Elimination Mode

```bash
python main.py \
    --mode elimination \
    --season 2024 \
    --competition FSAE \
    --question "What is the minimum roll hoop height?" \
    --options "800mm" "900mm" "1000mm" "1200mm"
```

### Audit Mode

```bash
python main.py \
    --mode audit \
    --season 2024 \
    --competition FSAE \
    --question "What are the impact attenuator requirements?" \
    --output audit_report.json
```

## Running Tests

```bash
# Run all tests
pytest fs_rules_llm/tests/ -v

# Run specific test file
pytest fs_rules_llm/tests/test_chunking.py -v

# Run with coverage
pytest fs_rules_llm/tests/ --cov=fs_rules_llm --cov-report=html
```

## Verification Steps

### 1. Verify Installation

```bash
python -c "import fs_rules_llm; print(fs_rules_llm.__version__)"
```

### 2. Verify Configuration

```bash
python -c "from fs_rules_llm.config.config_loader import get_config; c = get_config(); print(c.default_season, c.default_competition)"
```

### 3. Test with Sample Data

If you don't have actual PDFs yet, you can create a minimal test:

```bash
# Create a simple test PDF (requires creating test data)
# Then run through the pipeline
```

## Troubleshooting

### Issue: "Index not found for season/competition"

**Solution**: Make sure you've completed all 6 steps of the data ingestion workflow for that season/competition.

### Issue: "OPENAI_API_KEY environment variable not set"

**Solution**: Set the environment variable:
```bash
export OPENAI_API_KEY=your-key-here
```

### Issue: "No module named 'fs_rules_llm'"

**Solution**: Make sure you're running from the repository root and the virtual environment is activated.

### Issue: "faiss-cpu not found"

**Solution**: Install FAISS manually:
```bash
pip install faiss-cpu
```

### Issue: Validation errors during chunking

**Solution**: Review the errors file:
```bash
cat fs_rules_llm/data/processed/2024_FSAE_errors.json
```

Adjust chunking parameters or use `--strict false` for less strict validation.

## Best Practices

1. **One Index Per Season/Competition**: Never mix rules from different seasons
2. **Validate Before Indexing**: Always run validation before building indices
3. **Test with Known Questions**: Use verified questions to test accuracy
4. **Monitor Validation Warnings**: Review warnings to improve chunking
5. **Keep Logs**: Use `--log` in quiz mode to track reasoning
6. **Audit Mode for Debugging**: Use audit mode when answers seem incorrect

## Directory Structure After Setup

```
FsRuleBot/
├── fs_rules_llm/
│   ├── data/
│   │   ├── raw/
│   │   │   └── 2024/
│   │   │       └── FSAE/
│   │   │           └── FSAE_Rules_2024.pdf
│   │   ├── processed/
│   │   │   ├── 2024_FSAE_sections.json
│   │   │   ├── 2024_FSAE_chunks.json
│   │   │   ├── 2024_FSAE_chunks_validated.json
│   │   │   └── 2024_FSAE_embeddings.npy
│   │   └── indices/
│   │       └── 2024_FSAE/
│   │           ├── index.faiss
│   │           └── metadata.pkl
│   ├── ingestion/
│   ├── embeddings/
│   ├── query/
│   ├── modes/
│   ├── config/
│   ├── examples/
│   └── tests/
├── main.py
├── requirements.txt
└── README.md
```

## Next Steps

1. Add your PDF rulebooks to `fs_rules_llm/data/raw/`
2. Run the ingestion pipeline for each season/competition
3. Test with verified questions from `fs_rules_llm/examples/verified_questions.md`
4. Start using the system for registration quiz preparation
5. Report any issues or improvements

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the examples in `fs_rules_llm/examples/`
3. Run in audit mode to debug answers
4. Open an issue on GitHub

## Security Notes

- Never commit API keys or `.env` files
- Don't commit large PDF files to git (use .gitignore)
- Keep embeddings and indices local (listed in .gitignore)
- Review all answers before using in official contexts
