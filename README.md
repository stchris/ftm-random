# ftm-random

Generate random [followthemoney](https://followthemoney.tech) entities.

# Usage

```
$ uvx ftm-random --help
Usage: ftm-random [OPTIONS]

  Generate random followthemoney entities.

Options:
  --count INTEGER  Number of entities to generate.
  --schema TEXT    FTM schema name (can be specified multiple times).
  --random-schema  Use a random schema for each entity.
  --outfile TEXT   JSONL output file (leave this out for stdout)
  --help           Show this message and exit.
```