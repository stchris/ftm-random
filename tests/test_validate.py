"""Integration test: generate entities and validate them with `uvx followthemoney validate`."""

import json
import subprocess

from click.testing import CliRunner
from followthemoney import model

from ftm_random.main import generate_entities

runner = CliRunner()

# All non-abstract schemas
ALL_SCHEMAS = [name for name, s in model.schemata.items() if not s.abstract]


def parse_output(result):
    return [json.loads(line) for line in result.output.strip().splitlines()]


def validate_entities(entities):
    """Run entities through `uvx followthemoney validate` and return parsed output."""
    input_lines = "\n".join(json.dumps(e) for e in entities)
    proc = subprocess.run(
        ["uvx", "followthemoney", "validate"],
        input=input_lines,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"validate failed: {proc.stderr}"
    return [json.loads(line) for line in proc.stdout.strip().splitlines()]


def normalize(entity):
    """Add default fields that validate injects, for comparison."""
    out = dict(entity)
    out.setdefault("referents", [])
    out.setdefault("datasets", [])
    return out


class TestValidateAllSchemas:
    """Generate 5 entities per schema across all non-abstract schemas and validate."""

    def test_all_schemas_validate_unchanged(self):
        args = []
        for name in ALL_SCHEMAS:
            args += ["--schema", name]
        args += ["--count-per-schema", "100"]

        result = runner.invoke(generate_entities, args)
        assert result.exit_code == 0

        entities = parse_output(result)
        assert len(entities) == 100 * len(ALL_SCHEMAS)

        validated = validate_entities(entities)
        assert len(validated) == len(entities)

        for original, after in zip(entities, validated):
            assert normalize(original) == after, (
                f"Mismatch for {original.get('schema')} entity {original.get('id')}"
            )


class TestValidateConnected:
    """Generate connected entities and validate them."""

    def test_connected_entities_validate_unchanged(self):
        result = runner.invoke(
            generate_entities,
            [
                "--schema",
                "Person",
                "--schema",
                "Company",
                "--schema",
                "Directorship",
                "--schema",
                "Ownership",
                "--schema",
                "Associate",
                "--connected",
                "--count-per-schema",
                "10",
            ],
        )
        assert result.exit_code == 0

        entities = parse_output(result)
        assert len(entities) == 50

        validated = validate_entities(entities)
        assert len(validated) == len(entities)

        for original, after in zip(entities, validated):
            assert normalize(original) == after, (
                f"Mismatch for {original.get('schema')} entity {original.get('id')}"
            )


class TestValidateRandomSchema:
    """Generate entities with --random-schema and validate."""

    def test_random_schema_entities_validate_unchanged(self):
        result = runner.invoke(
            generate_entities,
            ["--random-schema", "--count", "1000"],
        )
        assert result.exit_code == 0

        entities = parse_output(result)
        assert len(entities) == 1000

        validated = validate_entities(entities)
        assert len(validated) == len(entities)

        for original, after in zip(entities, validated):
            assert normalize(original) == after, (
                f"Mismatch for {original.get('schema')} entity {original.get('id')}"
            )
