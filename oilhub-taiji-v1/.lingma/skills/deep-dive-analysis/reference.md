# Deep Dive Analysis - Reference Guide

## Detailed Methodology

### The Red-Green-Refactor Loop for Debugging

This skill adapts the TDD red-green-refactor pattern for debugging:

1. **RED**: Reproduce the failure
   - Create a minimal test case that demonstrates the bug
   - Ensure it fails consistently
   - Document the exact error message and conditions

2. **GREEN**: Find the fix
   - Trace the call chain to identify root cause
   - Form hypotheses about what's broken
   - Test each hypothesis systematically
   - Find the minimal change that makes the test pass

3. **REFACTOR**: Clean up
   - Once fixed, improve code quality if needed
   - Add regression tests
   - Document the finding

### Hypothesis Testing Framework

For each hypothesis you generate:

```markdown
**Hypothesis N**: [Clear statement of what you think is wrong]

**Prediction**: If this hypothesis is correct, then [observable behavior]

**Test**: [Specific command, log statement, or check to run]

**Result**: [PASS/FAIL] + actual observed behavior

**Conclusion**: [Keep/reject/refine hypothesis]
```

### Call Chain Tracing Techniques

#### 1. Symbol-Based Tracing

Use `search_symbol` to find relationships:

```
search_symbol queries:
- relation: "calls" → What does this function call?
- relation: "called_by" → Who calls this function?
- relation: "references" → What variables/types does it use?
- relation: "referenced_by" → Where is this symbol used?
```

Build the chain incrementally:
```
entry_point()
  ↓ calls
middleware.process()
  ↓ calls
service.execute()
  ↓ references
config.setting  ← Check this value
```

#### 2. Data Flow Tracing

Follow the data through the system:

```
Input: user_request.data
  → parsed by parser.validate()
  → transformed by transformer.normalize()
  → stored by repository.save()
  → returned as response.json()
```

At each step, ask:
- What transformations happen here?
- Could this transformation introduce the bug?
- What assumptions does this step make?

#### 3. Boundary Analysis

Identify where the bug crosses boundaries:

| Boundary Type | Examples | Common Issues |
|--------------|----------|---------------|
| Module | src/ → lib/ | Version mismatches, API changes |
| Service | API → Database | Connection timeouts, query errors |
| Language | Python → C extension | Type conversion, memory issues |
| Network | Client → Server | Serialization, encoding issues |

### Root Cause Categories

When you identify the root cause, categorize it:

1. **Logic Error**: Code doesn't implement intended logic
   - Off-by-one errors
   - Wrong conditional
   - Missing edge case handling

2. **Data Error**: Valid code, invalid/unexpected data
   - Null/undefined values
   - Type mismatches
   - Malformed input

3. **Configuration Error**: Code and data are correct, config is wrong
   - Environment variables
   - Feature flags
   - Connection strings

4. **Concurrency Error**: Race conditions, deadlocks
   - Shared state without synchronization
   - Order-dependent operations
   - Resource contention

5. **Dependency Error**: External component failure
   - Library bugs
   - API changes
   - Infrastructure issues

### Validation Strategies

#### Instrumentation Techniques

```python
# Add strategic logging
logger.debug(f"Variable X = {x} at line 42")

# Assert assumptions
assert x is not None, "X should never be None here"

# Trace execution
import traceback
traceback.print_stack()
```

#### Isolation Techniques

```bash
# Run with minimal dependencies
python -c "from module import func; func(test_input)"

# Binary search through commits
git bisect start
git bisect bad HEAD
git bisect good <known-good-commit>
```

#### Regression Testing

After fixing, ensure the bug doesn't return:

```python
def test_bug_123_fixed():
    """Regression test for issue #123"""
    result = function_under_test(input_that_triggered_bug)
    assert result == expected_value
```

## Tool Reference

### search_symbol

Find code symbols and their relationships.

**Parameters:**
- `symbol`: The symbol name to search for
- `relation`: One of: calls, called_by, references, referenced_by, extends, extended_by, implements, implemented_by, contains, contained_by, overrides, overridden_by, all, none

**Example:**
```
Query: Find what calls the authenticate function
symbol: "authenticate"
relation: "called_by"
```

### search_codebase

Semantic search across the codebase.

**Parameters:**
- `query`: Natural language description of what you're looking for
- `key_words`: Up to 3 important keywords

**Example:**
```
Query: "authentication middleware that validates JWT tokens"
key_words: "auth,jwt,middleware"
```

### get_problems

Check for compile/lint errors in specific files.

**Parameters:**
- `file_paths`: Array of absolute file paths

**Use when:** User mentions errors in a file, or after making changes

### Bash

Execute shell commands.

**Common uses:**
- Running tests: `pytest tests/test_auth.py`
- Checking git status: `git diff`
- Running the application: `npm start`
- Installing dependencies: `pip install -r requirements.txt`

## Anti-Patterns to Avoid

### 1. Shallow Analysis

**Bad:** "The error is caused by a null pointer exception."

**Good:** "The NullPointerException at AuthService.java:42 occurs because getUserById() returns null when the user doesn't exist in the database. This happens because the query on line 38 uses LEFT JOIN instead of INNER JOIN, allowing users with no associated profile to return null profiles."

### 2. Unverified Assumptions

**Bad:** "The database connection is probably timing out."

**Good:** "Hypothesis: Database connection timeout. Test: Check logs for 'Connection timed out' messages. Result: FAIL - No timeout messages found. Alternative: Check if credentials are valid..."

### 3. Vague Recommendations

**Bad:** "You should add better error handling."

**Good:** "Add a try-catch block around the database query on line 38-42 that catches SQLException and returns a descriptive error message including the user ID that was looked up."

### 4. Ignoring Context

Always read the surrounding code before making claims. A function might look buggy in isolation but be correct given how it's called.

## Performance Considerations

When analyzing performance issues:

1. **Measure first**: Don't guess, profile
   ```bash
   python -m cProfile script.py
   node --prof app.js
   ```

2. **Identify hotspots**: Focus on code that runs frequently or processes large datasets

3. **Check algorithmic complexity**: O(n²) vs O(n log n) matters at scale

4. **Look for N+1 queries**: Database queries in loops

5. **Consider caching opportunities**: Repeated expensive computations

## Security Analysis Checklist

When reviewing for security:

- [ ] Input validation on all external data
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] Authentication checks on protected routes
- [ ] Authorization checks for resource access
- [ ] Sensitive data not logged or exposed
- [ ] Dependencies up to date (no known CVEs)
