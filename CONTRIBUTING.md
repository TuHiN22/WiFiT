# Contributing to WiFiT

Thank you for your interest in contributing to WiFiT!

## Legal and Attribution

### License
WiFiT v3.0.0+ is licensed under the MIT License. By contributing, you agree that your contributions will be licensed under the same terms.

### Attribution
WiFiT builds upon concepts and code from multiple sources. When contributing significant algorithmic or architectural changes, please include appropriate attribution:

- **W8RootWifiHKV2** - Menu system and UI design patterns
- **FARHAN-Shot** - Clean architecture principles
- **OneShotPin** - WPS PIN algorithm implementations
- **Pixiewps** - Pixie Dust attack methodology

## Development Setup

### Prerequisites
- Python 3.10 or higher
- Git
- For Android/Termux testing: Rooted Android device with Termux

### Local Setup
```bash
# Clone the repository
git clone https://github.com/TuHiN22/WiFiT.git
cd WiFiT

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install WiFiT in editable mode
pip install -e .

# Run tests
pytest

# Run with coverage
pytest --cov=wifit_core --cov=wifit --cov-report=html
```

## Code Standards

### Security Requirements
- **NEVER use `shell=True`** in subprocess calls
- All subprocess operations MUST use argv lists
- Every external operation MUST have a finite timeout
- Validate all user input (interface names, BSSIDs, PINs)
- Use bounded retries and resource limits
- Credential files MUST use mode 0600
- Process termination MUST be conservative and identity-verified

### Code Style
- Follow PEP 8
- Use type hints (Python 3.10+ syntax)
- Run `ruff` before committing
- Maximum line length: 100 characters
- Use dataclasses for structured data
- Prefer dependency injection over global state

### Testing Requirements
- All new features MUST include tests
- Target ≥85% overall coverage
- Target ≥90% for critical modules (scanner, PIN generation, WPS lifecycle, process management, reporters)
- Tests MUST NOT transmit RF signals
- Use fake/mock tools for subprocess-dependent tests
- Include both unit and integration tests

### Testing Best Practices
```python
# Good: Deterministic, isolated, fast
def test_pin_generation_algorithm():
    generator = PINGenerator()
    pin = generator.generate("pin24", "AA:BB:CC:DD:EE:FF")
    assert len(pin) == 8
    assert pin.isdigit()

# Bad: Requires real hardware, non-deterministic
def test_live_wps_attack():
    # DON'T DO THIS IN AUTOMATED TESTS
    result = attack_real_network("00:11:22:33:44:55")
    assert result.successful
```

### Documentation
- Docstrings for all public functions, classes, and modules
- Include type hints and parameter descriptions
- Explain security-sensitive operations
- Document limitations and assumptions
- Update CHANGELOG.md for all user-facing changes

## Contribution Process

### 1. Create an Issue
Before starting work, create an issue describing:
- The problem or feature
- Proposed solution
- Security implications (if any)
- Testing approach

### 2. Fork and Branch
```bash
# Fork the repository on GitHub
git clone https://github.com/YOUR_USERNAME/WiFiT.git
cd WiFiT
git checkout -b feature/your-feature-name
```

### 3. Develop
- Write code following the standards above
- Add tests for new functionality
- Update documentation
- Run quality checks:
  ```bash
  pytest                          # All tests pass
  pytest --cov                    # Coverage ≥85%
  ruff check .                    # No lint issues
  mypy wifit_core                 # Type check passes
  bandit -r wifit_core            # No high-severity findings
  python -m compileall wifit_core # Compiles without errors
  ```

### 4. Commit
```bash
git add -A
git commit -m "feat: Add deterministic PIN enumeration

- Implement enumerate_all_pins() with exact 11,000 coverage
- Add resumable session with atomic saves
- Include comprehensive tests

Refs #123"
```

Commit message format:
- **feat:** New feature
- **fix:** Bug fix
- **docs:** Documentation only
- **test:** Test additions or corrections
- **refactor:** Code restructure without behavior change
- **perf:** Performance improvement
- **security:** Security enhancement

### 5. Push and Pull Request
```bash
git push origin feature/your-feature-name
```

Open a Pull Request with:
- Clear description of changes
- Reference to related issue(s)
- Test results and coverage report
- Screenshots (if UI changes)
- Confirmation that quality checks pass

### 6. Code Review
- Address reviewer feedback promptly
- Keep commits atomic and well-described
- Rebase onto main if requested
- Be open to suggestions

## What to Contribute

### High-Priority Areas
- Additional WPS PIN algorithms with test vectors
- Improved Android/Termux compatibility detection
- Better error messages and recovery suggestions
- Performance optimizations (especially scanner)
- Documentation improvements
- Test coverage improvements

### Medium-Priority Areas
- Additional export formats
- Enhanced progress reporting
- Logging improvements
- Configuration file support
- Plugin/extension system

### Low-Priority Areas
- UI/UX enhancements (keep ANSI style consistent)
- Additional platforms (Desktop Linux, WSL)
- IDE integrations

### Out of Scope
- GUI applications (WiFiT is terminal-only)
- Non-WPS attacks (stay focused on WPS)
- Cloud/remote execution
- Proprietary dependencies
- Breaking changes to established APIs without migration path

## Hardware Testing

WiFiT's core functionality requires:
- Wireless interface supporting monitor mode
- Root/superuser access
- Compatible wireless chipset (Broadcom, Atheros, Ralink, etc.)

### Test Lab Setup
If contributing hardware-dependent features:
1. Set up an isolated test environment
2. Use dedicated access points (not production networks)
3. Document hardware configurations
4. Provide test results in PR description

## Questions?

- Open an issue for general questions
- Use Discussions for longer conversations
- Check existing issues before creating new ones

## Code of Conduct

- Be respectful and constructive
- Focus on the code, not the person
- Assume good intentions
- Help newcomers
- Use this tool ethically and legally

Thank you for contributing to WiFiT! Your efforts help make WiFi security assessment more accessible and reliable.
