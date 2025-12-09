# Test Suite

This directory contains the test suite for the Mahjong Monte Carlo simulation project.

## Running Tests

### Run all tests with coverage report:
```bash
pytest tests/ --cov=mahjong_sim --cov-report=term-missing --cov-report=html
```

### Run tests without coverage:
```bash
pytest tests/ -v
```

### Run a specific test file:
```bash
pytest tests/test_simulation.py -v
```

### Run a specific test:
```bash
pytest tests/test_simulation.py::test_simulation_runs -v
```

## Coverage Requirements

- **Minimum coverage**: 60%
- **Current coverage**: ~65.56%

Coverage reports are generated in:
- Terminal output: `--cov-report=term-missing`
- HTML report: `htmlcov/index.html`
- XML report: `coverage.xml`

## Test Files

- `test_simulation.py`: Basic simulation tests
- `test_simulation_extended.py`: Extended simulation tests including utility calculation
- `test_strategies.py`: Strategy function tests (defensive/aggressive)
- `test_scoring.py`: Scoring function tests
- `test_players.py`: Player and NeutralPolicy tests
- `test_table.py`: Table simulation tests
- `test_utils.py`: Utility and statistics function tests

## Configuration

Pytest configuration is in `pytest.ini` at the project root. It includes:
- Coverage settings (minimum 60%)
- Test discovery patterns
- Coverage exclusions (experiments, tests, cache)

