.PHONY: clean coverage develop doc release requirements test venvs

clean:
	find . -name '*pyc' -delete
	find . -name '__pycache__' -delete

coverage:
	py.test --cov=bfh --cov-report=term-missing tests/

develop:
	pip install -r build-requirements.txt

doc:
	virtualenv -ppython3 venv-doc
	venv-doc/bin/pip install -r requirements.txt
	venv-doc/bin/pip install sphinx
	venv-doc/bin/pip install -e .
	make -C doc html
	rm -rf doc/site
	cp -r doc/_build/html doc/site
	cp doc/_config.yml doc/site/_config.yml
	rm -rf venv-doc
	# **********************************************************
	# now run git subtree push --prefix doc/site origin gh-pages
	# **********************************************************

release:
	rm -rf dist/
	venv2/bin/python setup.py bdist_wheel
	venv3/bin/python setup.py bdist_wheel sdist

requirements:
	pip install -r requirements.txt

test:
	python -m unittest discover tests/

venvs:
	virtualenv -ppython2 venv2
	venv2/bin/pip install -r requirements.txt
	venv2/bin/pip install -r build-requirements.txt
	virtualenv -ppython3 venv3
	venv3/bin/pip install -r requirements.txt
	venv3/bin/pip install -r build-requirements.txt
