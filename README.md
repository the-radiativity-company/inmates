# inmates

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

# Deployment

(forthcoming)
