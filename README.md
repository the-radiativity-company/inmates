# inmates
a tool for collating inmate rosters

# Setup
This project is written in `python` and currently uses `make` as a buildtool (see [this post](https://stackoverflow.com/questions/32127524/how-to-install-and-use-make-in-windows) for getting `make` on windows).
If you would like to render a deployable artifact, you will need [docker](https://docs.docker.com/get-docker/).
To start, though, a `virtualenv` will do.
Run the following to build your venv and 'source' it's context:

* `make`
* `source inmates-venv/bin/-activate`

Now you can run `pip list` to see that the `inmates` CLI tool was installed.
Execute the `inmates` command to see available subcommands.

# Contributing
(forthcoming)

# Deployment
(forthcoming)
