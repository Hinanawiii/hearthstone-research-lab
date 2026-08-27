.PHONY: test lint typecheck check smoke package

test:
	python -m unittest discover -s tests -v

lint:
	ruff check .

typecheck:
	mypy src/cardlab

check: lint typecheck test

smoke:
	cardlab autoresearch --backend mock --episodes 2 --eval-games 2 --run-dir runs/ci-smoke

package:
	python -m build

