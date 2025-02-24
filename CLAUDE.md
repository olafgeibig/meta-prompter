# meta-prompter Development Guidelines

## Commands
- **Test**: `pytest` or `python -m pytest`
- **Test single file**: `pytest tests/path_to_test.py`
- **Test specific function**: `pytest tests/path_to_test.py::test_function_name`
- **Package management**: `uv` (see uv.lock)
- **Run app**: `python -m meta_prompter.main`

## Code Style
- Python 3.12+ with full type hints
- Follow PEP 8 style guide
- Prefer pathlib over os.path for filesystem operations
- Small, focused functions/methods with single responsibilities
- Docstrings for all public modules, functions, classes, methods
- Explicit exception handling (catch specific exceptions)
- Meaningful variable/method names
- Use list/dict/set comprehensions when appropriate
- Prefer composition over inheritance
- Use dataclasses for data containers when appropriate
- Use logging for debugging (see utils/logging.py)

## Testing
- Use pytest as the testing framework
- Aim for 100% test coverage for new code
- Write tests for all public methods/functions
- Use fixtures, parameterized tests, and mocking
- Keep tests independent and idempotent