# ftm-random

Generate random [followthemoney](https://followthemoney.tech) entities.

# Usage

Run it with `uvx` (requires [uv](https://docs.astral.sh/uv/)).

```
$ uvx ftm-random
```

or install it with pip:

```
$ pip install ftm-random
```

<!-- help-start -->
```
$ ftm-random --help
Usage: ftm-random [OPTIONS] COMMAND [ARGS]...

  Generate random followthemoney entities.

Options:
  --help  Show this message and exit.

Commands:
  connected  Generate connected random followthemoney entities.
  entities   Generate random followthemoney entities.
  inbox      Generate a realistic email inbox for one Person entity.
  list       List all available FTM schemata with their type and...
```
<!-- help-end -->

# Development

This project uses [uv](https://docs.astral.sh/uv) and [prek](https://prek.j178.dev/).

Run tests with:

```
$ uv run pytest
```

or run tests and linters with:

```
$ prek run
```
