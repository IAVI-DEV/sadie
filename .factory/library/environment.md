# Environment

- **Python**: 3.14.4
- **Package manager**: poetry
- **Install**: `poetry install --with dev`
- **Test runner**: pytest (configured with `-x` in pytest.ini)
- **Formatting**: black (line length 120)
- **Type checking**: pyright
- **Pre-commit hooks**: `pre-commit run --all-files`

## Environment Variables

- `SADIE_USE_GERMLINES_MODULE`: Use local germlines (default: true) vs deprecated G3 API
