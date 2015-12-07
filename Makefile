# just run unittests

.PHONY: test
# -B : don't generate bytecode
# -m : run the module, unittest. Verbose. Look in ./tests/ for tests
test:
	python -B -m unittest discover -v -s ./tests/
