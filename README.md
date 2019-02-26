# Validation node

## Getting started

TODO: add a "Getting started guide"

## Development

For development, you need [Docker](https://www.docker.com/get-started) and [Python 3.7](https://www.python.org/downloads/release/python-370/).
You can use a local Blockchain, like [Ganache](https://truffleframework.com/ganache).

Environment variables get pulled from `.env` file. You can create one from `env` file which is in the root of this repository:
```bash
cp env .env
```
Make sure you set all the environment variables in `.env` file.

### Local Python Environment

Even if the application is running in Docker container you will want to have python library dependencies installed locally, so we use virtual environment.

Install virtualenv package with pip:
```bash
pip3 install virtualenv
```

Create virtual environment:
```bash
virtualenv <DESIRED_PATH_TO_VIRTUALENV>/<VENV_NAME> --python=python3
```

Now activate virtual environment:
```bash
source <DESIRED_PATH_TO_VIRTUALENV>/<VENV_NAME>/bin/activate
``` 

Then install dependencies by running:
```bash
pip install -r app/requirements.txt
```

### Running a node

To run a node:

```bash
docker run -d -p 6379:6379 --name redis redis
docker build -t validation-node:1.0.0 app/
docker run -p 80:5000 --env-file=.env --link redis validation-node:1.0.0
```

Validation node health check should be accessible at `http://localhost:80/health`

### Running a cluster of nodes

To run a cluster with 3 nodes:

```bash
docker-compose up
```

Nodes are accessible on localhost with ports `81`, `82` and `83`. Each node has its own Ethereum address, which need to be set in `env ` file.
