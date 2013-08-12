VERSION=1.1

test:
	python -u indicator.py

clean:
	find . -name \*.pyc -delete

install: sdist
	sudo pip install --upgrade dist/task-indicator-$(VERSION).tar.gz

sdist:
	python setup.py sdist
