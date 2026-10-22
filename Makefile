PROJECT_NAME = inmates
VENV = .venv
PYTHON = $(VENV)/bin/python
INMATES = $(VENV)/bin/inmates
TESTDIR = tests


all: install

.PHONY: build # builds a distributable wheel into dist/
build: $(VENV)
	@uv build

.PHONY: clean # deletes build residues, virtual environment, and python metafiles
clean: clean-build clean-venv clean-pyc

.PHONY: clean-build # deletes all build residues
clean-build:
	@rm -rf build dist *.egg-info

.PHONY: clean-pyc # deletes python metafiles
clean-pyc:
	@find . -name '__pycache__' -not -path './$(VENV)/*' -exec rm -rf {} +
	@find . -name '*.py[co]' -not -path './$(VENV)/*' -delete

.PHONY: clean-venv # deletes virtualenv
clean-venv:
	@rm -rf $(VENV)

.PHONY: commands # lists all Makefile commands
commands:
	@echo
	@tput bold setaf 2; echo $(PROJECT_NAME); tput sgr0; echo
	@grep --color=never -E '^\.PHONY: [a-z-]+ #' $(MAKEFILE_LIST) | sed -E 's/^\.PHONY: ([a-z-]+) # (.*)/  ->  \1\t\2/' | sort | expand -t 20
	@echo

.PHONY: image # builds a docker image
image:
	@docker build -t $(PROJECT_NAME):local .

.PHONY: image-run # runs the scraper inside the image, writing to ./outdir
image-run:
	@docker run --rm -v $(CURDIR)/outdir:/project/outdir $(PROJECT_NAME):local

.PHONY: install # creates the virtual environment and installs the project in editable mode
install: $(VENV)
	@uv pip install -q -e '.[dev]'

$(VENV):
	@uv venv -q $(VENV)

.PHONY: new-spider # creates a new spider: make new-spider NAME=county [FORCE=true]
new-spider: $(VENV)
ifeq ($(NAME),)
	$(error NAME not specified)
endif
	@$(PYTHON) -m scrapy genspider -t init $(NAME) - $(if $(FORCE), --force)

.PHONY: reinstall # rebuilds the virtual environment from scratch
reinstall: clean-venv install

.PHONY: scraper-run # runs spiders: make scraper-run [OUTDIR=dir] [ROSTER=name]
scraper-run: $(VENV)
	@$(INMATES) collate $(if $(OUTDIR),-o $(OUTDIR),) $(if $(ROSTER),-r $(ROSTER),)

.PHONY: scraper-load # loads scraped JSON into the database: make scraper-load [INDIR=outdir] [DB=inmates.db]
scraper-load: $(VENV)
	@$(INMATES) load -i $(or $(INDIR),outdir) -d $(or $(DB),inmates.db)

.PHONY: tests # runs all tests
tests: $(VENV)
	@$(PYTHON) -m pytest -q $(TESTDIR)

.PHONY: tree # prints the directory structure
tree:
	@tree -C $(CURDIR) -I '.*|$(VENV)|__pycache__|*.egg-info|build|dist|outdir'
