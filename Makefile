VERSION=1.40
PYTHON=python

test:
	-pep8 src/taskindicator/*.py

clean:
	find . -regex '.*\.\(pyc\|orig\)$$' -delete

install: sdist
	sudo pip install --upgrade dist/task-indicator-$(VERSION).tar.gz
	rm -rf MANIFEST dist

sdist: test
	python setup.py sdist

release: test
	$(PYTHON) setup.py sdist upload --sign
	-xdg-open https://pypi.python.org/pypi/task-indicator/$(VERSION)
