.PHONY: check

check:
	flake8
	MYPYPATH=stubs/ mypy .
	pytest
