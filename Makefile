VERSION=1.1
PYTHON=python

test:
	python -u indicator.py

clean:
	find . -name \*.pyc -delete

install: sdist
	sudo pip install --upgrade dist/task-indicator-$(VERSION).tar.gz

sdist:
	python setup.py sdist

release:
	$(PYTHON) setup.py sdist upload --sign
