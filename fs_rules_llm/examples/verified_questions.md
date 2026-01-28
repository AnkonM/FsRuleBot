# Verified Question Examples for Formula Student Rules

This file contains manually verified correct answers for regression testing.
Each question has been validated against actual Formula Student rules.

## Purpose

These golden test cases serve multiple purposes:
1. **Regression Testing**: Ensure system accuracy doesn't degrade
2. **Citation Validation**: Verify that cited rules actually support the answers
3. **Format Verification**: Confirm output format compliance
4. **Hallucination Detection**: Catch any unsupported claims

## Format

Each entry includes:
- Question text
- Correct answer
- Rule citations
- Supporting quotes (verbatim from rules)
- Notes on common pitfalls

---

## Example 1: Wheelbase Requirement

**Question**: What is the minimum wheelbase requirement for FSAE 2024?

**Correct Answer**: The minimum wheelbase is 1525 mm.

**Rule References**:
- FSAE 2024 Rules – T.2.3.1

**Supporting Quotes**:
> "The wheelbase, measured as per T.1.1, must be at least 1525 mm."

**Notes**:
- This is a straightforward factual question
- The answer must include the exact measurement
- Must cite the specific clause number

---

## Example 2: Brake System Requirements

**Question**: Is a brake light required on FSAE vehicles?

**Correct Answer**: Yes

**Rule References**:
- FSAE 2024 Rules – T.7.5.1

**Supporting Quotes**:
> "The vehicle must be equipped with a brake light mounted at the rear of the vehicle."

**Notes**:
- This is a Yes/No quiz question
- The rule explicitly requires it
- Don't infer from "recommended" language

---

## Example 3: Ambiguous Question

**Question**: What is the recommended tire pressure for wet conditions?

**Correct Answer**: Not explicitly specified in the rules.

**Rule References**: N/A

**Supporting Quotes**: N/A

**Notes**:
- The rules don't specify tire pressures
- This is left to team discretion
- System should NOT provide engineering recommendations
- System should NOT say "typically 20 psi" or similar

---

## Example 4: Multiple Choice - Elimination Required

**Question**: What is the minimum thickness for the main roll hoop tubing?

**Options**:
- A) 1.0 mm
- B) 1.2 mm
- C) 1.6 mm
- D) 2.0 mm

**Correct Answer**: C

**Rule References**:
- FSAE 2024 Rules – T.3.2.1

**Supporting Quotes**:
> "Primary structure of the main roll hoop must use tubing with minimum wall thickness of 1.6 mm."

**Notes**:
- Options A and B can be eliminated as too thin
- Option D exceeds minimum but C is the stated minimum
- Answer should be the minimum specified, not a safe larger value

---

## Example 5: Table-Based Information

**Question**: What is the minimum impact attenuator energy absorption requirement for FSAE?

**Correct Answer**: The impact attenuator must absorb a minimum of 7350 joules of energy.

**Rule References**:
- FSAE 2024 Rules – T.4.3.1, Table T.4.3.1

**Supporting Quotes**:
> "Energy Absorption: 7350 J minimum"

**Notes**:
- Information comes from a table
- Must cite both the clause and the table
- Include units (joules)

---

## Example 6: Conditional Requirement

**Question**: Is a fire extinguisher required if the vehicle uses electric propulsion only?

**Correct Answer**: Not explicitly specified in the rules.

**Rule References**: (See T.8.1.1 for general requirements)

**Supporting Quotes**: N/A

**Notes**:
- Rules may specify fire extinguisher for combustion engines
- EV-specific requirements may differ
- If not explicitly stated for EVs, answer is "not specified"
- Do NOT assume requirements carry over

---

## Testing Instructions

### Automated Testing

```python
# Example test case
def test_wheelbase_requirement():
    generator = create_answer_generator("2024", "FSAE")
    result = generator.generate_answer(
        "What is the minimum wheelbase requirement?",
        mode="qa"
    )
    
    # Check answer contains correct value
    assert "1525 mm" in result['answer']
    
    # Check citation exists
    assert "T.2.3.1" in str(result['citations'])
    
    # Check quote verification
    assert result['validation']['quotes_verified']
```

### Manual Verification

1. Run each question through the system
2. Compare output to expected answer
3. Verify citations match
4. Confirm quotes are verbatim
5. Check that no unsupported claims are made

### Citation Verification

For each answer:
1. Locate the cited clause in the source PDF
2. Verify the quote appears verbatim
3. Confirm the quote actually supports the answer
4. Check that no claims are made without citation

---

## Common Issues to Test For

### ❌ Hallucination

**Bad**: "The minimum wheelbase is 1525 mm, which is standard for most racing series."
**Why Bad**: Second clause is not from rules (general knowledge)
**Good**: "The minimum wheelbase is 1525 mm." (only what rules state)

### ❌ Inference

**Bad**: "While not explicitly stated, teams typically use 20 psi for wet tires."
**Why Bad**: Making assumptions not in rules
**Good**: "Not explicitly specified in the rules."

### ❌ Missing Citations

**Bad**: "The brake light must be red and mounted at the rear."
**Why Bad**: No rule citation provided
**Good**: "The brake light must be red (T.7.5.2) and mounted at the rear (T.7.5.1)."

### ❌ Paraphrasing Instead of Quoting

**Bad**: "The rules say the wheelbase needs to be at least 1525mm."
**Why Bad**: Paraphrased, not quoted
**Good**: Quote: "The wheelbase... must be at least 1525 mm."

### ❌ Mixing Rule Versions

**Bad**: Using 2023 rules when asked about 2024
**Why Bad**: Must never mix seasons
**Good**: Only retrieve from specified season

---

## Adding New Test Cases

When adding new verified questions:

1. **Manually verify** the answer against the PDF
2. **Find exact page number** and clause ID
3. **Copy quote verbatim** (do not paraphrase)
4. **Test both positive and negative cases**
5. **Include edge cases and ambiguities**
6. **Document why the answer is correct**

---

## Regression Test Frequency

- Run after any changes to:
  - Chunking logic
  - Retrieval algorithm
  - Prompt templates
  - LLM model version
  - Answer validation

**All tests must pass before deploying changes.**
