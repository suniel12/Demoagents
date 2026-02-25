.PHONY: test test-live record-mocks demo-break

test:
	@echo "Running all tests (mock mode, no API keys needed)..."
	pytest tests/ -v --tb=short

test-live:
	@echo "Running live tests (requires OPENAI_API_KEY)..."
	pytest tests/ --live -v --tb=short

record-mocks:
	@echo "Recording mock responses from live API (requires OPENAI_API_KEY)..."
	rm -f tests/fixtures/mock_responses.yaml
	pytest tests/ --live --record-golden -v --tb=short

demo-break:
	@echo "Running regression tests against live API..."
	pytest tests/test_regression.py --live -v --tb=long
