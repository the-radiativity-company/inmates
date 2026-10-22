# inmates

[![CI build status](https://github.com/the-radiativity-company/inmates/workflows/CI/badge.svg)](https://github.com/the-radiativity-company/inmates/actions)[![Cron build status](https://github.com/the-radiativity-company/inmates/workflows/Cron/badge.svg)](https://github.com/the-radiativity-company/inmates/actions)

This project is being conducted on behalf of Chicago Community Bond Fund.

# Problem Space

Chicago Community Bond fund is struggling to meet capacity. New donations have increased their ability to conduct their mission at a much larger scale as they are growing their efforts state-wide.

One bottleneck is the various sites that have inmate information. The current process is to manually check these sites to see if they have new information. This information is to be used for advocacy purposes. 

It is difficult for volunteers to track the current list of county sites to check.

It is even more difficult for a person to verify whether there is new information on that site or not. It is also difficult to then combine that manually collected information together to create actionable data.

Luckily, these are all spaces where an automated solution can greatly increase the efficiency of human efforts!

# Goals

- Be able to extract as much information about inmates as each county makes available in an automated fashion. (scrapers/spiders), the most important data points (if available) being:  
    * bail amount 
    * name 
    * DOB 
    * sex 
    * race
    * booking date
    * charge
    
- Be able to know when county sites have been updated with new data.(snapshots)

- Programatically persist all scraped inmate information to a secure place where authorized CCBF individuals can access and use for their advocacy work. For rosters not easily scraped, we will provide a way for data to also be manually entered (via api, database, etc.).

- Through the above efforts, we'll help cut down on the amount of human effort to conduct routine tasks, and we can build a rich dataset not only of inmate information, but also of the ways counties differ in their dissemination practices. This entire process can potentially generate valuable information to help affect policy goals and ultimately end the cash bail system in Illinois.(advocacy, policy)

# Contributing

There are many ways to contribute to any of the above goals!

The biggest current need is for code contributions to begin scrapping the data from the various county websites. These are currently documented [here](https://docs.google.com/spreadsheets/d/1bzZqnXFybr_Hf7iTdalVAZa9VjLtRouhIMsgOoy6ARA/edit?usp=drive_web&ouid=117025765328028106544).

This work is in early stages, so expect more detailed process documentation.

Each website will require it's own scraper(called "spiders" in Scrapy--the Python webscrapping framework we're using) of varying complexity.

# Setup

This project is written in `python` (3.12 or newer) and uses `make` plus [uv](https://docs.astral.sh/uv/) as its build tooling (see [this post](https://stackoverflow.com/questions/32127524/how-to-install-and-use-make-in-windows) for getting `make` on windows).
If you would like to render a deployable artifact, you will need [docker](https://docs.docker.com/get-docker/).
To start, though, a virtual environment will do.
Run the following to build it and activate it:

- `make`
- `source .venv/bin/activate`

Now you can run `pip list` to see that the `inmates` CLI tool was installed.
Execute the `inmates` command to see available subcommands (`inmates csv -c 'Roster Link'` can be helpful).

# Roster Index

`inmates.csv` has a row for each of Illinois' 102 counties and is the source of truth for where rosters live.

| Column | Meaning |
|---|---|
| `Roster Link` | the page that lists people in custody; blank when the county publishes none |
| `PDF` | whether the roster is a PDF rather than HTML |
| `Platform` | the vendor behind the roster (`newworld`, `archonix`, `bluhorse`, ...) so one spider can serve many counties |
| `Status` | what the link did when last probed: `ok`, `moved`, `blocked`, `http 404`, `unreachable`, or `none` |
| `Checked` | the date of that probe |
| `Notes` | what a human saw there |

`make survey` (or `inmates survey`) refetches every link, stamps `Status` and `Checked`, and fills in `Platform` when it can recognize the vendor.
Run it before working on a spider; a county whose status is not `ok` needs a new link before it needs code.

# Development

In service of the aforestated goals, a `scrapy.Spider` is written for each roster *platform*: the software a vendor sells to many sheriffs (NewWorld InmateInquiry, Archonix XJail, Bluhorse, ...).
A county whose roster is home-grown gets a spider of its own.
The `Platform` column of `inmates.csv` decides which spider reads a county; `inmates collate` passes the county's `Roster Link` as `domain` and its slug as `county`.
Most everything needed to develop a such a scraper is provided within the project.
Please see an overview of the project layout, below (generated via `make tree`--use `make commands` to see all available commands):

```
inmates/
├── commissary
│   ├── adams.pdf
│   ├── ...
│   └── woodford.html
├── inmates
│   ├── cli.py
│   ├── commands
│   │   ├── ...
│   │   └── cmd_somecommand.py
│   ├── scraper
│   │   ├── items.py
│   │   ├── ...
│   │   ├── settings.py
│   │   └── spiders
│   │       ├── adams.py
│   │       ├── ...
│   │       └── woodford.py
│   └── utils.py
└── tests
    ├── fixtures
    │   ├── adams.json
    │   ├── ...
    │   └── woodford.json
    ├── test_adams.py
    ├── ...
    └── test_woodford.py
```

When scraping data from a roster, here are four components at play:

 * the site to be scraped
 * the spider
 * the data scraped
 * expectations on scraped data

The 'sites to be scraped' are all housed in the "commissary/" directory so there's less of a need to reach out to the world wide web.
Spiders live in the "inmates/scraper/spiders/" directory, named for the platform they read (`newworld.py`) or, failing that, the county (`adams.py`).
To get started on a new spider, simply run the following:

```bash
make new-spider NAME=new
```
where "new" is the name of your `NewSpider` at "inmates/scraper/spiders/new.py".
Use the `FORCE=true` flag if you'd like to overwrite an existing spider.

To run spiders, use the `inmates collate` subcommand.
Results can be saved using the `-o/--outdir` option that accepts a path to a directory where collected records are to be stored.
An _individual_ county can be scraped using the `-r/--roster` option.
A helpful approach during development of a spider's `.parse` method is to leverage setting "breakpoints".
Placing `ipdb.set_trace(context=15)` in the path of code to be executed, will pause execution once the "breakpoint" is hit (where the `context` keyword governs the scope of code visible when execution is paused).
With execution paused, defined variables can be probed and response parsing can be explored in opened shell.

# Deployment

The `Scrape` workflow (`.github/workflows/scrape.yml`) runs daily and on manual dispatch. Each run:

1. downloads the current `inmates.db` from the S3 bucket, if one exists
2. runs `inmates collate -o outdir` to scrape every county to `<county>.json`
3. runs `inmates load -i outdir -d inmates.db` to upsert those records into the database
4. syncs the JSON to `s3://<bucket>/snapshots/<date>/` and uploads the database to `s3://<bucket>/current/inmates.db`

The same flow runs locally:

```bash
make scraper-run OUTDIR=outdir          # or ROSTER=macon for one county
make scraper-load INDIR=outdir DB=inmates.db
sqlite3 inmates.db 'SELECT * FROM current_custody'
```

`inmates.db` is the **current-custody** model: one `person` row per person a county lists, upserted on every scrape with `first_seen`, `last_seen`, and `in_custody`; `booking` and `charge` rows replaced on every scrape; and a `scrape_run` row per county per run recording whether the scrape was `ok`, `empty`, or `missing`.
Only a successful, non-empty scrape marks absent people as released, so a dead site never looks like a mass release.
Every row keeps the county's raw record as JSON.
The dated snapshots in S3 preserve full history for a longitudinal model later.
