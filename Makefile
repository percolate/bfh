.PHONY: requirements test dist doc

doc:
	pdoc --overwrite --html --html-dir ./doc/html bfh

requirements:
	pip install -r requirements.txt

test:
	python -m unittest discover tests/

dist:
	python setup.py bdist_wheel sdist
