# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-02-28

### Bug Fixes

- Fix E741 ruff linter errors: rename ambiguous variable l to line


- Fix ruff formatting in main.py



### Features

- Add --connected flag to link generated entities via edge schemas

When --connected is used, node entities (e.g. Person, Company) are
generated first, then edge entities (e.g. Directorship, Associate)
have their entity-reference properties wired to actual IDs from the
node pool, producing a connected graph.


- Add tests for --connected flag

Three test classes covering:
- _pick_entity_id: range matching, schema inheritance, empty pool
- generate_random_entity with entity_pool: wiring source/target props
- CLI integration: output counts, ID referencing, emission order,
  error cases, multiple edge schemas, backward compat without flag


- Add pytest and ruff as dev dependencies; fix formatting

- Add [project.optional-dependencies] dev group with pytest>=8.0 and ruff>=0.9
- Add [tool.pytest.ini_options] and [tool.ruff] config sections to pyproject.toml
- Run ruff format to fix line-length and style issues in main.py and tests/


- Add ruff lint and format checks to CI; update lock file

- Add ruff check and ruff format --check steps to test.yml workflow
- Regenerate uv.lock to include pytest and ruff dev dependencies


- Add --list flag to display all FTM schemas with type and description

Prints a formatted table of every schema in the FTM model, showing its
name, whether it acts as a node or edge in --connected mode, and its
human-readable description. Also adds tests for the new flag.


- Add git-cliff changelog generation
- Create GitHub release on tag push

### Other

- Merge pull request #1 from stchris/claude/add-connected-flag-cSfG0
- Merge pull request #2 from stchris/claude/add-pytest-ruff-fixes-ZTXtQ
- Automate README --help output in release workflow

- Add <!-- help-start --> / <!-- help-end --> markers around the help
  block in README.md so the update script can find and replace it
- Fix README: add missing --connected option, update --outfile description
- In release.yml: bump contents permission to write, install the project
  with uv sync, run a Python snippet to capture ftm-random --help and
  rewrite the marked section, then commit and push to main before building


- Merge pull request #3 from stchris/claude/automate-readme-help-output-wav0b
- Merge pull request #4 from stchris/claude/add-list-command-VJcXq
- Merge pull request #5 from stchris/claude/fix-ruff-linter-Bogrf
- Merge pull request #6 from stchris/claude/fix-formatting-check-E9isP
- Merge pull request #7 from stchris/claude/add-changelog-generation-SklhT
- Merge pull request #8 from stchris/claude/github-release-workflow-gdIoI

### Refactor

- Extract release notes from CHANGELOG instead of re-running git-cliff

## [0.1.2] - 2026-02-27

### Other

- Proper packaging
- V0.1.2 prep

## [0.1.1] - 2026-02-27

### Features

- Add script

## [0.1.0] - 2026-02-27

### Features

- Add test workflow

### Other

- Initial commit
- Release


