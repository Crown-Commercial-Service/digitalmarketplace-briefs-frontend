# Digital Marketplace Briefs Frontend

[![Coverage Status](https://coveralls.io/repos/alphagov/digitalmarketplace-briefs-frontend/badge.svg?branch=master&service=github)](https://coveralls.io/github/alphagov/digitalmarketplace-briefs-frontend?branch=master)
[![Requirements Status](https://requires.io/github/alphagov/digitalmarketplace-briefs-frontend/requirements.svg?branch=master)](https://requires.io/github/alphagov/digitalmarketplace-briefs-frontend/requirements/?branch=master)

Frontend briefs application for the digital marketplace.

- Python app, based on the [Flask framework](http://flask.pocoo.org/)

## Quickstart

Install dependencies, run migrations and run the app
```
make run-all
````

## Setup

The briefs frontend app requires access to the API. The location and access tokens for 
the API is set with environment variables.


For development you can either point the environment variables to use the 
preview environment's `API` boxes, or use local API instances if you have
them running:

```
export DM_DATA_API_URL=http://localhost:5000
export DM_DATA_API_AUTH_TOKEN=<auth_token_accepted_by_api>
```

Where `DM_DATA_API_AUTH_TOKEN` is a token accepted by the Data API 
instance pointed to by `DM_API_URL`.

### Create and activate the virtual environment

```
python3 -m venv ./venv
source ./venv/bin/activate
```

### Upgrade dependencies

Install new Python dependencies with pip

```pip install -r requirements-dev.txt```

[Install frontend dependencies](https://github.com/alphagov/digitalmarketplace-briefs-frontend#front-end) with yarn and gulp

```
yarn
```

### Run the tests

To run the whole testsuite:

```
make test
```

To only run the JavaScript tests:

```
make test-javascript
```

### Run the development server

To run the Briefs Frontend App for local development you can use the convenient run 
script, which sets the required environment variables to defaults if they have
not already been set:

```
make run-app
```

More generally, the command to start the server is:
```
python application.py runserver
```

The app runs on port 5005 by default. Use the app at [http://127.0.0.1:5005/](http://127.0.0.1:5005/)

### Updating application dependencies

`requirements.txt` file is generated from the `requirements-app.txt` in order to pin
versions of all nested dependecies. If `requirements-app.txt` has been changed (or
we want to update the unpinned nested dependencies) `requirements.txt` should be
regenerated with

```
make freeze-requirements
```

`requirements.txt` should be commited alongside `requirements-app.txt` changes.

### Using FeatureFlags

To use feature flags, check out the documentation in (the README of)
[digitalmarketplace-utils](https://github.com/alphagov/digitalmarketplace-utils#using-featureflags).

## Front-end

Front-end code (both development and production) is compiled using [Node](http://nodejs.org/) and [Gulp](http://gulpjs.com/).

### Requirements

You need Node (try to install the version we use in production -
 see the [base docker image](https://github.com/alphagov/digitalmarketplace-docker-base/blob/master/base.docker)).

To check the version you're running, type:

```
node --version
```

### Installation

[How to install yarn](https://yarnpkg.com/en/docs/install)
To install the required Node modules, type:

```
yarn
```

## Frontend tasks

[YARN](https://yarnpkg.com/en/) is used for all frontend build tasks. The commands available are:

- `yarn run frontend-build:development` (compile the frontend files for development)
- `yarn run frontend-build:production` (compile the frontend files for production)
- `yarn run frontend-build:watch` (watch all frontend+framework files & rebuild when anything changes)


## Frontend tests

To run the JavaScript tests, navigate to `spec/javascripts/support/` and open `LocalTestRunner.html` in a browser.
