## forksearch

```
> python main.py -h
usage: main.py [-h] [--token TOKEN] [--host HOST] [--port PORT] [--username USERNAME] [--password PASSWORD] [-f FILE] [-r REPO] [-q] [-y] [-t]

ForkSearch CLI

options:
  -h, --help            show this help message and exit
  --token TOKEN         Github token (Default token with environment variable GH_TOKEN)
  --host HOST           Neo4j host
  --port PORT           Neo4j port
  --username USERNAME   Neo4j username
  --password PASSWORD   Neo4j password
  -f FILE, --file FILE  file containing list of owner/repo
  -r REPO, --repo REPO  owner/repo (Default: dbrumley/forksearch)
  -q, --quiet           Not printing repo information
  -y, --yes             Yes to all confirmation
  -t, --trace           Trace back to the parent repository
```

## Usage

1. `cd` into project directory.

2. Create a virtual environment.

```bash
$ make venv
```

3. Activate it.

```bash
$ source venv/bin/activate
```

4. Install development dependencies with editable mode to test the CLI.

```bash
$ make install
```

## Take forksearch for a spin

First, you need to create a Github access token. You'll need repo and email permissions.

Then,

```bash
$ export GH_TOKEN=<GH_TOKEN>
$ cd forksearch
$ python main.py dbrumley/calculator
```

NOTE: Installation isn't working. To be fixed :)

### Test with Docker

CLI commands can be tested with Docker.

1. Build an image for the CLI.

   Image is tagged with the same name as the `cli_command`.

```bash
$ make docker-image
```

2. Run the command inside the container.

```bash
$ docker-run --rm forksearch init
```

## Documentation

1. Install documentation-related dependencies.

```bash
$ make docs
```

2. Serve the docs locally.

```bash
$ make serve-docs
```

## Distribution

> **NOTE**
>
> Make sure you have account in [PyPI](https://pypi.org/account/register/) before you try this out.

To publish you CLI to PyPI, run:

```bash
$ make distributions
```

`dist` directory will be created inside your project directory. Upload it to PyPI using:

```bash
$ twine dist/*
```

## Help

For help related to make commands.

```bash
$ make help
```
