.PHONY: test test-live baseline compare

test:
	pytest tests/test_rag.py -v

test-live:
	pytest tests/test_rag.py -v --live

baseline:
	python save_baseline.py

compare:
	# Run tests specifying the baseline to compare against
	AGENT_MODEL=$(MODEL) pytest tests/test_rag.py --agentci-compare "rag-v1-gpt4o-mini"
