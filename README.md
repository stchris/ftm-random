# ftm-random

Generate random [followthemoney](https://followthemoney.tech) entities.

# Usage

<!-- help-start -->
```
$ ftm-random --help
Usage: ftm-random [OPTIONS]

  Generate random followthemoney entities.

Options:
  --count INTEGER  Number of entities to generate.
  --schema TEXT    FTM schema name (can be specified multiple times).
  --random-schema  Use a random schema for each entity.
  --connected      Link edge entities (e.g. Directorship) to other generated
                   entities.
  --outfile TEXT   JSONL output file or '-' for STDOUT
  --list           List all available FTM schemas with their type and
                   description.
  --help           Show this message and exit.
```
<!-- help-end -->
