PYTHON = python3
SRC    = src/main.py
VENV   = .venv/bin/activate

.PHONY: all install test demo compile clean

all: install compile test

install:
	$(PYTHON) -m venv .venv
	. $(VENV) && pip install -r requirements.txt -q

compile:
	. $(VENV) && for f in examples/*.f; do \
		name=$$(basename $$f .f); \
		$(PYTHON) $(SRC) $$f -o examples/$$name.vm; \
	done

test:
	. $(VENV) && $(PYTHON) -m pytest --no-cov -q

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; true
	rm -f src/parser.out src/parsetab.py out.vm
