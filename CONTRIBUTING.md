# Contributing to QED Vacuum Thrust Control

Thank you for your interest in contributing to the QED Vacuum Thrust Control project! We welcome contributions from researchers, developers, and enthusiasts working on quantum propulsion systems, physics simulations, and AI navigation.

## Table of Contents

- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community Guidelines](#community-guidelines)
- [Reporting Issues](#reporting-issues)

## Getting Started

Before contributing, please:

1. Read our [Code of Conduct](CODE_OF_CONDUCT.md)
2. Check existing [issues](https://github.com/jhofseth/QED-Vacuum-Thrust-Control/issues) and [pull requests](https://github.com/jhofseth/QED-Vacuum-Thrust-Control/pulls)
3. Review the [project roadmap](README.md#roadmap)
4. Join discussions via [GitHub Discussions](https://github.com/jhofseth/QED-Vacuum-Thrust-Control/discussions) (if enabled)

**First-time contributors:** Look for issues labeled `good-first-issue` or `help-wanted`.

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **Bug fixes:** Fix issues in simulations, equations, or AI navigation
- **New features:** Implement items from the roadmap or propose new capabilities
- **Documentation:** Improve README, add examples, write tutorials
- **Tests:** Increase test coverage, add edge case tests
- **Performance:** Optimize simulation speed or memory usage
- **Research:** Contribute insights on QED theory, EGDPP model, or propulsion physics

### Discussion Before Implementation

For significant changes, please discuss via:

- **GitHub Issues:** For bug reports and feature requests (use templates)
- **Email:** Contact maintainers at auagpt@usa.com
- **Pull Request Draft:** Create a draft PR for early feedback

This helps ensure your contribution aligns with project goals and avoids duplicate work.

## Development Setup

### Prerequisites

- **Python:** 3.12 or higher
- **Poetry:** For dependency management
- **Git:** For version control

### Installation

1. **Fork and clone the repository:**

```bash
git clone https://github.com/YOUR_USERNAME/QED-Vacuum-Thrust-Control.git
cd QED-Vacuum-Thrust-Control
```

2. **Install Poetry (if not already installed):**

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. **Install dependencies:**

```bash
poetry install --with dev,docs
```

4. **Activate the virtual environment:**

```bash
poetry shell
```

5. **Verify installation:**

```bash
pytest tests/
python simulations/thrust_model.py --b_opposing 50 --frequency 100
```

### Project Structure

```
QED-Vacuum-Thrust-Control/
├── simulations/          # Core simulation code
│   ├── equations.py      # Physics equations and calculations
│   └── thrust_model.py   # Main thrust simulation
├── ai/                   # AI navigation system
│   └── navigation.py     # MIMO neural network for 6DOF control
├── tests/                # Test suite
│   ├── test_equations.py
│   ├── test_thrust_model.py
│   └── test_navigation.py
├── examples/             # Usage examples
├── docs/                 # Documentation
└── assets/               # Images, media files
```

## Pull Request Process

### Before Submitting

1. **Create a feature branch:**

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

2. **Make your changes:**
   - Write clear, documented code
   - Follow coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests locally:**

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=simulations --cov=ai --cov-report=html

# Run specific test file
pytest tests/test_equations.py -v
```

4. **Check code quality:**

```bash
# Format code
black simulations/ ai/ tests/

# Check linting
flake8 simulations/ ai/ tests/ --max-line-length=100

# Type checking (optional)
mypy simulations/ ai/ --ignore-missing-imports
```

5. **Commit your changes:**

```bash
git add .
git commit -m "Add feature: brief description"
```

Use clear, descriptive commit messages following [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Adding or updating tests
- `refactor:` Code refactoring
- `perf:` Performance improvements

### Submitting the Pull Request

1. **Push to your fork:**

```bash
git push origin feature/your-feature-name
```

2. **Create a Pull Request:**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your fork and branch
   - Fill out the PR template with:
     - Clear description of changes
     - Related issue numbers (e.g., "Closes #123")
     - Testing performed
     - Screenshots (if UI changes)

3. **PR Requirements:**
   - All tests must pass (CI/CD checks)
   - Code coverage should not decrease
   - At least one maintainer approval required
   - No merge conflicts with `main` branch

4. **Address Review Feedback:**
   - Respond to reviewer comments
   - Make requested changes
   - Push updates to the same branch

5. **Versioning:**
   - Maintainers will handle version bumps following [SemVer](https://semver.org/)
   - Format: `MAJOR.MINOR.PATCH` (e.g., `0.2.1`)

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use [Black](https://black.readthedocs.io/) for formatting (line length: 100)
- Use type hints where appropriate
- Write docstrings for all public functions/classes

**Example:**

```python
def force_vector(chi: float, B: float, grad_h2: np.ndarray, 
                 A: float, rho: float) -> np.ndarray:
    """
    Calculate the force vector for QED vacuum propulsion.
    
    Parameters:
    chi (float): Susceptibility
    B (float): Magnetic field strength (T)
    grad_h2 (np.ndarray): Gradient of metric perturbation squared
    A (float): Area (m²)
    rho (float): Density (kg/m³)
    
    Returns:
    np.ndarray: Force vector (N)
    """
    grad_h2 = np.asarray(grad_h2)
    return chi * B**2 * grad_h2 * A * rho
```

### Physics and Math

- Use clear variable names matching physics notation when possible
- Add units in comments or docstrings
- Cite papers/sources for equations in comments
- Use NumPy/SciPy for numerical operations
- Use SymPy for symbolic mathematics

### AI/ML Code

- Document model architectures clearly
- Include training/inference examples
- Save model checkpoints with meaningful names
- Track hyperparameters

## Testing Guidelines

### Test Requirements

- All new features must include tests
- Bug fixes should include regression tests
- Aim for >80% code coverage
- Tests should be fast and deterministic

### Test Structure

```python
import pytest
import numpy as np

class TestEquations:
    """Test physics equation implementations."""
    
    def test_force_vector_basic(self):
        """Test force vector with basic inputs."""
        chi, B = 1e-10, 50.0
        grad_h2 = np.array([1.0, 0.0, 0.0])
        A, rho = 1.0, 1000.0
        
        result = force_vector(chi, B, grad_h2, A, rho)
        
        assert result.shape == (3,)
        assert result[0] > 0
        
    def test_force_vector_zero_field(self):
        """Test force vector with zero magnetic field."""
        result = force_vector(1e-10, 0.0, np.array([1,0,0]), 1.0, 1000.0)
        assert np.allclose(result, 0.0)
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_equations.py

# With coverage
pytest tests/ --cov=simulations --cov=ai --cov-report=html

# Parallel execution
pytest tests/ -n auto
```

## Documentation

### Code Documentation

- Use clear docstrings (Google or NumPy style)
- Include parameter types, units, and return values
- Add usage examples for complex functions
- Document assumptions and limitations

### README Updates

Update `README.md` when adding:
- New features or capabilities
- New dependencies
- New command-line options
- Breaking changes

### Examples

Add examples to `examples/` for:
- New simulation scenarios
- Integration patterns
- Advanced usage

## Community Guidelines

### Communication

- **Be respectful:** Treat all contributors with respect
- **Be constructive:** Provide helpful, actionable feedback
- **Be patient:** Remember that contributors may have different experience levels
- **Give credit:** Acknowledge others' work and ideas

### Scientific Integrity

- **Cite sources:** Properly credit research papers and prior work
- **Be rigorous:** Verify equations and physics calculations
- **Share data:** Make simulations reproducible
- **Acknowledge uncertainty:** Be clear about theoretical limitations

### Code Review Etiquette

**As a reviewer:**
- Focus on code quality, not personal style preferences
- Explain the "why" behind suggestions
- Acknowledge good work
- Be timely with reviews

**As an author:**
- Don't take feedback personally
- Ask questions if feedback is unclear
- Thank reviewers for their time
- Fix issues promptly

## Reporting Issues

### Bug Reports

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) and include:

- Clear description of the bug
- Steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, Python version, dependencies)
- Error messages/tracebacks
- Minimal reproducible example

### Feature Requests

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md) and include:

- Problem statement
- Proposed solution
- Alternative approaches considered
- Use cases and benefits
- Alignment with project roadmap

### Security Issues

**Do not create public issues for security vulnerabilities.**

Instead, email security concerns to: auagpt@usa.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fixes (if any)

## Recognition

Contributors will be:
- Listed in project acknowledgments
- Credited in release notes
- Mentioned in relevant documentation

Significant contributors may be invited to join as project maintainers.

## License

By contributing, you agree that your contributions will be licensed under the MIT License, the same license covering this project. See [LICENSE](LICENSE) for details.

## Questions?

- **General questions:** Open a GitHub Discussion
- **Technical issues:** Create a GitHub Issue
- **Private inquiries:** Email auagpt@usa.com

## Attribution

This contributing guide is adapted from open-source best practices and the Contributor Covenant, version 3.0, available at https://www.contributor-covenant.org/version/3/0/

Thank you for contributing to advancing QED vacuum propulsion research! 🚀
