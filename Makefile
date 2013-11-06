VERSION=1.10
PYTHON=python

test:
	pep8 src/taskindicator/*.py

clean:
	find . -name \*.pyc -delete

install: sdist
	sudo pip install --upgrade dist/task-indicator-$(VERSION).tar.gz
	rm -rf MANIFEST dist

sdist:
	python setup.py sdist

release:
	$(PYTHON) setup.py sdist upload --sign
