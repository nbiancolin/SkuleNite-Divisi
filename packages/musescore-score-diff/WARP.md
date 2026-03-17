# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

This is a Python package that creates visual diffs between two versions of MuseScore files by comparing their musical content and generating a new score that highlights the differences. The project is inspired by Greg Chapman and Francesco Fortino's "Music-score-diff" but is specialized for MuseScore files.

The core concept is to:
1. Parse two MuseScore files (old and new versions)
2. Extract and compare measures using XML parsing and content hashing
3. Use LCS (Longest Common Subsequence) algorithm to identify differences
4. Generate a visual diff score with colored annotations showing additions, deletions, and modifications

## Architecture

### Core Components

- **`src/musescore_score_diff/compute_diff.py`**: Main diff computation logic using LCS algorithm
- **`src/musescore_score_diff/utils.py`**: XML parsing, measure extraction, and hashing utilities  
- **`src/musescore_score_diff/display_diff.py`**: Visual diff rendering (currently empty/in development)
- **`__OLD/compute_diff.py`**: Previous implementation with more complex XML manipulation and visual highlighting

### Data Flow

1. **Measure Extraction**: `extract_measures()` parses uncompressed .mscx files and extracts measures with their XML content
2. **Content Hashing**: Each measure is hashed using MD5 after sanitization (removing EIDs and linkedMain elements)
3. **Diff Computation**: LCS algorithm compares measure sequences between files
4. **State Classification**: Measures are classified as UNCHANGED, MODIFIED, INSERTED, or REMOVED
5. **Visual Output**: (In development) Generate a new MuseScore file with visual annotations

### Key Algorithms

- **LCS (Longest Common Subsequence)**: Used to find common measures between two scores
- **XML Sanitization**: Removes MuseScore-specific metadata that shouldn't affect diff comparison
- **Content-based Hashing**: MD5 hashing of normalized XML content for fast measure comparison

## Common Development Tasks

### Environment Setup
```bash
# Activate virtual environment (if exists)
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Unix/Mac

# Install dependencies
pip install pytest colorama

# Set PYTHONPATH for development
$env:PYTHONPATH = "src"  # PowerShell
export PYTHONPATH="src"  # Bash
```

### Running Tests
```bash
# Run all tests with PYTHONPATH set
$env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m pytest tests\ -v

# Run specific test file
$env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m pytest tests\compute_diff_test.py -v

# Run single test
$env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m pytest tests\compute_diff_test.py::test_hash_measure -v
```

### File Structure

```
src/musescore_score_diff/        # Main package source
  ├── compute_diff.py            # LCS-based diff algorithm
  ├── utils.py                   # XML parsing and utilities
  ├── display_diff.py            # Visual diff rendering (WIP)
  └── __init__.py
tests/                          # Test files
  ├── fixtures/                 # Test MuseScore files
  │   ├── single-staff/         # Simple test cases
  │   ├── Test-Score/           # Complex multi-instrument scores
  │   └── Test-Score-2/
  ├── sample-output/            # Expected test outputs
  └── compute_diff_test.py      # Unit tests
__OLD/                          # Previous implementation (reference)
```

### Test Fixtures

The project includes MuseScore test files in multiple formats:
- **Uncompressed (.mscx)**: XML format used by current implementation
- **Compressed (.mscz)**: ZIP format containing .mscx and metadata
- **Single-staff vs Multi-staff**: Different complexity levels for testing

### Working with MuseScore Files

MuseScore files contain XML with specific structure:
- `<Score>` root element contains all musical data
- `<Staff>` elements contain measures for each instrument
- `<Measure>` elements contain the actual musical content (notes, rests, etc.)
- EID and linkedMain elements are MuseScore-specific metadata that should be ignored for diff purposes

### Known Issues

1. **Package Installation**: The pyproject.toml has configuration issues - use PYTHONPATH instead of pip install
2. **Test Assertions**: Some tests have incorrect expected values (check test failures)
3. **Visual Display**: The display_diff.py module is not yet implemented
4. **Complex Scores**: Multi-staff instruments (like piano) may need special handling

### Visual Diff Techniques (from __OLD implementation)

The previous implementation included advanced visual diff features:
- **Colored annotations**: Red for deleted content, green for added content
- **Measure highlighting**: Background coloring for changed measures  
- **Staff management**: Adding comparison staves next to originals
- **XML manipulation**: Direct modification of MuseScore XML for visual effects

### Development Notes

- The current implementation focuses on measure-level comparison using content hashing
- The LCS algorithm efficiently identifies common subsequences of measures
- XML sanitization is crucial for meaningful comparisons (removes transient MuseScore metadata)
- Future work involves implementing visual diff rendering in display_diff.py
