---
name: Bug Report
about: Report a bug to help us improve QED Vacuum Thrust Control
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description

<!-- A clear and concise description of what the bug is. -->

## To Reproduce

Steps to reproduce the behavior:

1. Go to '...'
2. Run command '...'
3. Execute function '...'
4. See error

**Minimal Reproducible Example:**

<!-- If applicable, provide a minimal code example or the exact command you ran -->

```bash
python simulations/thrust_model.py --b_opposing 50 --frequency 100
```

Or:

```python
from simulations.equations import force_vector
# Your code here
```

## Expected Behavior

<!-- A clear and concise description of what you expected to happen. -->

## Actual Behavior

<!-- What actually happened, including any error messages or unexpected outputs. -->

## Error Message/Traceback

<!-- If applicable, paste the full error message and traceback here -->

```
Paste error traceback here
```

## Screenshots/Logs

<!-- If applicable, add screenshots or additional logs to help explain the problem. -->

## Environment

**System Information:**
- OS: [e.g., Windows 11, macOS sonoma 14.2, Ubuntu 24.04]
- Python Version: [e.g., 3.12.3]
- Installation Method: [e.g., pip, poetry, conda]

**Dependency Versions:**

<!-- Run: pip list | grep -E "numpy|scipy|torch|matplotlib|sympy" -->
<!-- Or: pip freeze | grep -E "numpy|scipy|torch|matplotlib|sympy" -->

```
numpy==1.26.0
scipy==1.11.0
torch==2.1.0
matplotlib==3.8.0
sympy==1.12
```

**Repository Information:**
- Branch: [e.g., main, develop]
- Commit Hash: [e.g., abc1234 or "latest"]
- Installation: [e.g., `git clone` + `pip install -e .`]

## Additional Context

<!-- Add any other context about the problem here -->

- Related issues: #
- Workarounds attempted:
- Frequency of occurrence: [e.g., always, intermittent, only on certain systems]
- Impact on workflow:

## Priority Suggestion

<!-- Optional: Suggest a priority level based on impact -->

- [ ] **P0** - Critical: System crash, data loss, or complete failure of core functionality
- [ ] **P1** - High: Major feature broken, significant performance degradation, no workaround
- [ ] **P2** - Medium: Feature partially broken, workaround available, affects some users
- [ ] **P3** - Low: Minor issue, cosmetic problem, or edge case
- [ ] **P4** - Trivial: Documentation typo, formatting issue, or nice-to-have enhancement

**Justification:** <!-- Briefly explain your priority assessment -->

## Checklist

<!-- Please check the following before submitting -->

- [ ] I have searched existing issues to ensure this is not a duplicate
- [ ] I have provided a minimal reproducible example
- [ ] I have included the full error traceback
- [ ] I have specified my environment details
- [ ] I have described both expected and actual behavior

---

**Note:** For security vulnerabilities, please do NOT create a public issue. Instead, email security contact or use GitHub Security Advisories.
