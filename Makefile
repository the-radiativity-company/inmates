.PHONY: build clean clean-pyc clean-venv clean-install install publish reinstall test tree uninstall

SYSTEM_PYTHON = $(shell which python3)
PROJECT_NAME = $(shell basename $(CURDIR))
VENV = $(PROJECT_NAME)-venv
VENV_PYTHON = $(VENV)/bin/python
TESTDIR = tests/


all: venv install clean-install

venv:
	@if [ ! -d $(VENV) ]; then \
		$(SYSTEM_PYTHON) -m pip install virtualenv; \
		$(SYSTEM_PYTHON) -m virtualenv $(VENV) >/dev/null; \
	fi

venv-dir:
	@echo $(CURDIR)/$(VENV)

image:
	@docker build -t $(shell make image-tag) .

image-run:
	@docker run -it --env PORT=5000 --publish 5000:5000 $(PROJECT_NAME)

image-tag:
	@echo $(PROJECT_NAME):$(shell git tag | head -1)

image-remote-tag:
	@echo registry.heroku.com/$(PROJECT_NAME)/web

publish:
	@docker tag $(shell make image-tag) $(shell make image-remote-tag)
	@docker push $(shell make image-remote-tag)

release:
	@heroku container:release web

build: $(VENV) $(VENV_PYTHON)
	@$(VENV_PYTHON) setup.py bdist_wheel

install: $(VENV) $(VENV_PYTHON)
	@$(VENV_PYTHON) setup.py install --skip-build

uninstall: $(VENV) $(VENV_PYTHON) clean-install
	@$(VENV_PYTHON) -m pip uninstall $(PROJECT_NAME)

reinstall: uninstall install

tree:
	@tree -C $(CURDIR) -I '.*|$(VENV)|__pycache__|*.egg-info|build|dist'

clean: clean-install clean-venv clean-pyc

clean-install:
	@rm -rf *.egg-info
	@rm -rf build
	@rm -rf dist

clean-pyc:
	@find . -name '*.pyc' -exec rm -f {} +
	@find . -name '*.pyo' -exec rm -f {} +
	@find . -name '*~' -exec rm -f {} +
	@find . -name '__pycache__' -exec rm -fr {} +

clean-venv:
	@rm -rf $(VENV)

test: $(VENV_PYTHON) $(TESTDIR)
	@$(VENV_PYTHON) -m unittest discover $(TESTDIR)

targets:
	@echo
	@tput bold setaf 2; echo $(shell basename $(CURDIR)); echo
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' | sed 's/^/  ->  /'
	@tput sgr0
	@echo
