# GitHub Search Strategies & Repository Evaluation

Advanced techniques for finding and evaluating GitHub repositories for skill creation.

## GitHub Search Syntax

### Basic Search Operators

```
keyword                    # Simple keyword search
language:python            # Filter by language
stars:>=100                # Minimum stars
pushed:>2024-01-01        # Updated after date
license:mit                # Filter by license
```

### Combined Searches

``# Find Python PDF libraries with 100+ stars
PDF processing language:python stars:>=100

# Find recently updated repositories
image manipulation pushed:>2024-06-01 language:python

# Find popular, licensed repositories
REST API stars:>=1000 license:(mit OR apache)
```

### Search by Filename

```
filename:setup.py          # Find Python packages
filename:package.json      # Find Node.js projects
extension:md               # Find documentation
```

## Repository Quality Indicators

### Metrics to Check

| Metric | Good | Excellent | Notes |
|--------|------|-----------|-------|
| Stars | 100+ | 1000+ | Higher = more popular |
| Forks | 20+ | 100+ | Active community usage |
| Updated | <6 months | <1 month | Active maintenance |
| Issues | <100 open | Low open/closed ratio | Responsive maintainers |
| Watchers | 10+ | 50+ | Interest level |

### Red Flags to Avoid

- ⚠️ No commits in 1+ year
- ⚠️ Many open issues (100+)
- ⚠️ No LICENSE file
- ⚠️ Empty or minimal README
- ⚠️ Broken tests or failing builds
- ⚠️ No documentation or examples

## Evaluating Repository Structure

### Essential Files

```
✅ Must have:
├── README.md              # Project overview and usage
├── LICENSE                # Legal usage terms
├── requirements.txt       # Python dependencies
├── setup.py / setup.json  # Package configuration
└── examples/              # Usage examples

🔷 Nice to have:
├── docs/                  # Detailed documentation
├── tests/                 # Test suite
├── .github/workflows/     # CI/CD setup
└── CONTRIBUTING.md        # Contribution guidelines
```

### Code Organization

**Good structure:**
```
project/
├── src/                   # Source code
├── tests/                 # Tests
├── docs/                  # Documentation
├── examples/              # Examples
└── README.md              # Getting started guide
```

**Poor structure:**
```
project/
├── script.py              # Single file, no organization
├── test.py                # Tests mixed with code
└── README.txt             # Minimal documentation
```

## License Compatibility

### Permissive Licenses (Recommended)

| License | Can Use | Can Modify | Can Distribute | Commercial |
|---------|---------|------------|----------------|------------|
| MIT | ✅ | ✅ | ✅ | ✅ |
| Apache 2.0 | ✅ | ✅ | ✅ | ✅ |
| BSD | ✅ | ✅ | ✅ | ✅ |

### Restrictive Licenses (Use with Care)

| License | Can Use | Can Modify | Can Distribute | Commercial |
|---------|---------|------------|----------------|------------|
| GPL | ✅ | ✅ | ⚠️ | ❌ |
| LGPL | ✅ | ✅ | ⚠️ | ⚠️ |

**Recommendation:** Prefer MIT/Apache/BSD for maximum flexibility.

## API Design Evaluation

### Signs of Good API

```python
# ✅ Clear, intuitive API
library.process_document(file_path, output_format="pdf")
library.set_option("quality", "high")

# ❌ Confusing, poorly documented
library.doc_proc(f, fmt, opt, q)  # What do these mean?
```

### What to Look For

1. **Function names**: Clear, descriptive verbs
2. **Parameters**: Logical defaults, clear types
3. **Return values**: Consistent types, well-documented
4. **Error handling**: Meaningful exceptions
5. **Documentation**: Docstrings with examples

## Testing Repository Usability

### Quick Test Checklist

```bash
# 1. Can you install it?
pip install repository-name

# 2. Does it import correctly?
python -c "import library_name"

# 3. Can you run the examples?
cd examples/
python example_script.py

# 4. Are there tests?
python -m pytest tests/

# 5. Is documentation helpful?
python -c "help(library_name)"
```

### Common Installation Issues

**Issue:** Missing dependencies
```bash
# Check if dependencies are specified
cat requirements.txt
```

**Issue:** Python version incompatibility
```bash
# Check required Python version
grep -i "python" setup.py
```

**Issue:** System dependencies
```bash
# Check for non-Python dependencies
grep -E "(apt|yum|brew)" README.md
```

## Analyzing Repository Activity

### Using GitHub CLI (gh)

```bash
# Install: brew install gh

# View recent commits
gh repo view owner/repo --json latestCommit

# Check issue statistics
gh issue list --repo owner/repo --state open --limit 10

# View release history
gh release list --repo owner/repo
```

### Manual Assessment

```bash
# Check commit frequency
git log --since="6 months ago" --oneline | wc -l

# Check recent contributors
git shortlog -sn --since="6 months ago"

# Check commit message quality
git log --format="%s" -10
```

## Alternative Repository Sources

If GitHub doesn't have suitable repositories:

### Package Repositories

- **Python**: https://pypi.org/search/
- **Node.js**: https://www.npmjs.com/
- **Ruby**: https://rubygems.org/
- **Go**: https://pkg.go.dev/

### Code Libraries

- **Awesome Lists**: Search "awesome [topic]"
- **LibHunt**: https://www.libhunt.com/
- **OpenSource.com**: https://opensource.com/article

## Search Templates

### For Specific Functionality

``# PDF Processing
PDF processing language:python stars:>=100

# Image Manipulation
image manipulation language:python stars:>=500

# Data Visualization
data visualization charts language:python stars:>=100

# Web Scraping
web scraping crawler language:python stars:>=200

# API Clients
REST API client language:python stars:>=100
```

### For Specific Languages

``# Python Libraries
topic:python-library topic:utility stars:>=100

# JavaScript Libraries
topic:javascript topic:library stars:>=500

# Go Libraries
language:go topic:library stars:>=100
```

## Evaluating Niche Repositories

### When Options Are Limited

If few repositories exist:

1. **Lower standards**: Accept 50+ stars instead of 100+
2. **Check activity**: Recent commits are more important than stars
3. **Read issues**: See if maintainer is responsive
4. **Test thoroughly**: Verify it works for your use case
5. **Consider forks**: Someone may have improved the original

### Combining Multiple Libraries

Sometimes combining 2-3 small libraries is better than one large one:

```python
# Example: PDF processing pipeline
from lib1 import extract_text    # Text extraction
from lib2 import format_output   # Output formatting
from lib3 import send_api        # API integration
```
