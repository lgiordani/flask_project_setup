# Flask Project setup

This repository contains the project described in a series of blog posts that you can find [here](https://www.thedigitalcatonline.com/blog/2020/07/05/flask-project-setup-tdd-docker-postgres-and-more-part-1/).

The requirements of the project are the following:

* Use the same database engine in production, in development and for tests
* Run test on an ephemeral database
* Run in production with no changes other that the static configuration
* Have a command to initialise databases and manage migrations
* Have a way to spin up "scenarios" starting from an empty database, to create a sandbox where I can test queries
* Possible simulate production in the local environment

## License

The project is released under the MIT license (see `LICENSE.txt`).
