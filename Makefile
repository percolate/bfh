.PHONY: clean doc requirements test coverage venvs release

clean:
	find . -name '*pyc' -delete
	find . -name '__pycache__' -delete

doc:
	pdoc --overwrite --html --html-dir ./doc/html bfh

requirements:
	pip install -r requirements.txt

test:
	python -m unittest discover tests/

coverage:
	py.test --cov=bfh --cov-report=term-missing tests/

venvs:
	virtualenv -ppython2 venv2
	venv2/bin/pip install -r requirements.txt
	venv2/bin/pip install -r build-requirements.txt
	virtualenv -ppython3 venv3
	venv3/bin/pip install -r requirements.txt
	venv3/bin/pip install -r build-requirements.txt

release:
	rm -rf dist/
	venv2/bin/python setup.py bdist_wheel
	venv3/bin/python setup.py bdist_wheel sdist
