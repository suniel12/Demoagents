.PHONY: test test-live demo-break

test:
	@echo "Running all tests (mock mode, no API keys)..."
	pytest tests/ -v --tb=short

test-live:
	@echo "Running live tests (requires OPENAI_API_KEY)..."
	pytest tests/ -v --tb=short -m "not mock_only"

demo-break:
	@echo "Running break scenario demos..."
	pytest tests/test_regression.py -v --tb=long
