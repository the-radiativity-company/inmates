# inmates

[![CI build status](https://github.com/the-radiativity-company/inmates/workflows/CI/badge.svg)](https://github.com/the-radiativity-company/inmates/actions)

[![Cron build status](https://github.com/the-radiativity-company/inmates/workflows/Cron/badge.svg)](https://github.com/the-radiativity-company/inmates/actions)

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

Each website will require it's own scraper(called spiders in Scrapy, the Python webscrapping framework we're using) of varying complexity.

# Setup

This project is written in `python` and currently uses `make` as a buildtool (see [this post](https://stackoverflow.com/questions/32127524/how-to-install-and-use-make-in-windows) for getting `make` on windows).
If you would like to render a deployable artifact, you will need [docker](https://docs.docker.com/get-docker/).
To start, though, a `virtualenv` will do.
Run the following to build your venv and 'source' it's context:

- `make`
- `source inmates-venv/bin/-activate`

Now you can run `pip list` to see that the `inmates` CLI tool was installed.
Execute the `inmates` command to see available subcommands.

# Development

In service of the aforestated goals, a `scrapy.Spider` for each county will be created.
Most everything needed to develop a such a scraper is provided within the project.
Please see an overview of the project layout, below (generated via `make tree`):

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
Spiders live in the "inmates/scraper/spiders/" directory and there's to be _one for every site in the commissary/_.
Here's an example of the bare minimum needed to start a spider for a given county:

```python
class AdamsRoster(Spider):
    name = 'adams'

    def parse(self, response):
        pass
```

All that is required is the presence of a `.name` attribute and a `.parse` function.
To scrape the local site associated with each scraper, run `make fixtures` and see this sort of output:

```bash
❌ adams (Please yield data from the .parse method)
...
✅ woodford
```

The `AdamsRoster` spider, above, will definitely need some work, but the completed `WoodfordRoster` spider was successfully able to parse the site and produce data fixtures.
Fixtures generated by the woodford spider, can be found in the "tests/fixtures/" directory.
To ensure that the parsed data has the structure and content expected, assertions are written in an associated test module.
For the `WoodfordRoster`, those assertions would be found in "tests/test_woodford.py".

# Deployment

(forthcoming)
