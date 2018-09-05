# Validation node

## Getting started

Validation node environment is set up using [Docker](https://www.docker.com/get-started) (so make sure you have it installed).


First clone this repo.

```bash
git clone git@gitlab.com:eventum-dev/validation-node.git
cd validation-node
```

If you just want to run node(s) localy:

1.
```bash
docker build -t <IMAGENAME>:<TAG> app/
```
You may omit `:<TAG>` if you wish to have more versions.

2.
```bash
docker run -p <DESIRED_PORT>:5000 <IMAGENAME>:<TAG>
```

Validation node REST API is now accessible at `localhost:<DESIRED_PORT>`


## Dev setup

For development [Python 3.7](https://www.python.org/downloads/release/python-370/) is used, so have it installed.

### Local Python Environment
Even if application is running in Docker container you will want to have python library dependencies installed localy, so we use virtual environment.

Install virtualenv package with pip:
```bash
pip3 install virtualenv
```

Create virtual environment
```bash
virtualenv <DESIRED_PATH_TO_VIRTUALENV>/<VENV_NAME>
```
Optinally you set pass `--python=<PATH_TO_PYTHON3.7_BIN>` argument to specify which python you want installed.

Now activate virtual environment
```bash
source <DESIRED_PATH_TO_VIRTUALENV>/<VENV_NAME>/bin/activate
``` 

When virtual environment is created, make sure it is pointing to correct version of python in virtual environment.
```bash
which python
```
should output ```<PATH_TO_VIRTUALENV>/<VENV_NAME>/bin/python``` and
```bash
pip -V
```
should output ```<PATH_TO_VIRTUALENV>/<VENV_NAME>/lib/python3.7/site-packages/pip (python 3.7)```


### Environment variables

Environmental variables get pulled from `.env` file. You can create one from `env` file which is in root of this repo:
```bash
cp env .env
```

### Running in dev mode

Make sure you have set
```bash
FLASK_ENV=dev
FLASK_DEBUG=1
```
in your `.env` file. Now you can start the app on 2 different ways:

1. `docker-compose up`, and app is exposed on port `80`
or
2. `python app/application.py` and app is exposed at Flask's default port `5000` 






