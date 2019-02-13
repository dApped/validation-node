# Validation node

## Getting started

TODO: add getting started guide

## Development

For development you need [Docker](https://www.docker.com/get-started) and [Python 3.7](https://www.python.org/downloads/release/python-370/).

Environmental variables get pulled from `.env` file. You can create one from `env` file which is in root of this repo:
```bash
cp env .env
```
Make sure you set all the env variables.

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

Then install dependencies by running
```bash
pip install -r app/requirements.txt
```

### Running a node localy

For development you can use local blockchain, like [Ganache](https://truffleframework.com/ganache).

To run node localy:

```bash
docker run -d -p 6379:6379 --name redis redis
docker build -t validation-node:1.0.0 app/
docker run -p 80:5000 --env-file=.env --link redis validation-node:1.0.0
```

Validation node health check should be accessible at `http://localhost:80/health`

### Running node a cluster localy

To run validation node cluster with 3 nodes:

```bash
docker-compose up
```

Nodes are exposed on localhost ports `81`, `82` and `83`.
Each has its own ETH address which is assigned from locally available addresses.
