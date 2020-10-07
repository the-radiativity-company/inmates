SYSTEM_PYTHON = $(shell which python3)
PROJECT_NAME = $(shell basename $(CURDIR))
VENV = $(PROJECT_NAME)-venv
VENV_PYTHON = $(VENV)/bin/python
TESTDIR = tests
FIXTURESDIR = $(TESTDIR)/fixtures
SCRAPERDIR = inmates/scraper


all: venv install

.PHONY: build # builds a distributable artifact
build: $(VENV) $(VENV_PYTHON)
	@$(VENV_PYTHON) setup.py bdist_wheel

.PHONY: clean # deletes build residues, virtual environment, and python metafiles
clean: clean-build clean-venv clean-pyc

.PHONY: clean-build # deletes all build residues
clean-build:
	@rm -rf build
	@rm -rf dist

.PHONY: clean-pyc # deletes python metafiles
clean-pyc:
	@find . -name '*.pyc' -exec rm -f {} +
	@find . -name '*.pyo' -exec rm -f {} +
	@find . -name '*~' -exec rm -f {} +
	@find . -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-venv # deletes virtualenv
clean-venv:
	@rm -rf $(VENV)

.PHONY: commands # lists all Makefile commands
commands:
	@echo
	@tput bold setaf 2; echo $(shell basename $(CURDIR)); echo
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' | sed 's/^/  ->  /'
	@tput sgr0
	@echo

.PHONY: fixtures # generates test fixtures
fixtures: $(VENV_PYTHON) $(FIXTURESDIR)
	@$(VENV_PYTHON) $(FIXTURESDIR)

.PHONY: git-tag
git-tag:
	@echo $(shell git describe --tags)

.PHONY: image # builds a docker image
image:
	@docker build -t $(shell make image-tag) .

.PHONY: image-remote-tag # renders tag for pushing to remote container registry
image-remote-tag:
	@echo registry.heroku.com/$(PROJECT_NAME)/web

.PHONY: image-run # runs image container locally
image-run:
	@docker run -it --env PORT=5000 --publish 5000:5000 $(PROJECT_NAME)

.PHONY: image-tag # renders image tag for pushing to remote container registry
image-tag:
	@echo $(PROJECT_NAME):$(shell git tag | tail -1)

.PHONY: install # installs project and dep to virtual environment
install: build $(VENV) $(VENV_PYTHON) clean-build
	@$(VENV_PYTHON) -m pip install -r requirements.txt
	@$(VENV_PYTHON) -m pip install -e .

.PHONY: new-spider # creates a new spider
new-spider:
ifeq ($(NAME),)
	$(error NAME not specified)
endif
	@$(VENV_PYTHON) -m scrapy genspider -t init $(NAME) - $(if $(FORCE), --force)

.PHONY: publish # publishes docker image
publish:
	@docker tag $(shell make image-tag) $(shell make image-remote-tag)
	@docker push $(shell make image-remote-tag)

.PHONY: reinstall # uninstall then install
reinstall: uninstall install

.PHONY: release # deploy container
release:
	@heroku container:release web

.PHONY: scraper-run # runs scrapers and can store them locally envvar set
scraper-run:
	@$(VENV_PYTHON) $(SCRAPERDIR) $(if $(OUTDIR),$(OUTDIR),)

.PHONY: tests # runs all tests
tests: $(VENV_PYTHON) $(TESTDIR)
	@$(VENV_PYTHON) -m unittest discover $(TESTDIR)

.PHONY: tree # prints the directory structure
tree:
	@tree -C $(CURDIR) -I '.*|$(VENV)|__pycache__|*.egg-info|build|dist'

.PHONY: uninstall # uninstalls project and dep from virtual environment
uninstall: $(VENV) $(VENV_PYTHON) clean-install
	@$(VENV_PYTHON) -m pip uninstall $(PROJECT_NAME)
	@rm -rf *.egg-info

.PHONY: venv # builds the virtual environment
venv:
	@if [ ! -d $(VENV) ]; then \
		$(SYSTEM_PYTHON) -m pip install virtualenv --user; \
		$(SYSTEM_PYTHON) -m virtualenv $(VENV) >/dev/null; \
	fi
