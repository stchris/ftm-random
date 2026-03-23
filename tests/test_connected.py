import json

from click.testing import CliRunner
from followthemoney import model

from ftm_random.main import (
    _pick_entity_id,
    cli,
    generate_random_entity,
)

runner = CliRunner()


def parse_output(result):
    """Parse JSONL output into a list of entity dicts."""
    return [json.loads(line) for line in result.output.strip().splitlines()]


# ---------------------------------------------------------------------------
# _pick_entity_id
# ---------------------------------------------------------------------------


class TestPickEntityId:
    def test_picks_from_matching_schema(self):
        prop = model.get("Directorship").get("director")  # range = LegalEntity
        pool = {"Person": ["id-person-1", "id-person-2"]}
        picked = _pick_entity_id(prop, pool)
        assert picked in pool["Person"]

    def test_picks_across_multiple_compatible_schemas(self):
        prop = model.get("Directorship").get("director")  # range = LegalEntity
        pool = {"Person": ["id-p"], "Company": ["id-c"]}
        results = {_pick_entity_id(prop, pool) for _ in range(50)}
        # Both should be reachable since Person and Company are LegalEntities
        assert results == {"id-p", "id-c"}

    def test_respects_range_constraint(self):
        prop = model.get("Directorship").get("organization")  # range = Organization
        pool = {"Person": ["id-person"], "Company": ["id-company"]}
        results = {_pick_entity_id(prop, pool) for _ in range(50)}
        # Person is NOT an Organization, Company IS
        assert results == {"id-company"}

    def test_returns_none_when_no_match(self):
        prop = model.get("Directorship").get("organization")  # range = Organization
        pool = {"Person": ["id-person"]}
        assert _pick_entity_id(prop, pool) is None

    def test_returns_none_for_empty_pool(self):
        prop = model.get("Directorship").get("director")
        assert _pick_entity_id(prop, {}) is None


# ---------------------------------------------------------------------------
# generate_random_entity with entity_pool
# ---------------------------------------------------------------------------


class TestGenerateRandomEntityConnected:
    def test_entity_pool_wires_source_and_target(self):
        pool = {"Person": ["id-person-1"], "Company": ["id-company-1"]}
        entity = generate_random_entity("Directorship", entity_pool=pool)
        props = entity.to_dict()["properties"]
        # director accepts LegalEntity, so both Person and Company qualify
        assert props["director"][0] in ("id-person-1", "id-company-1")
        assert props["organization"] == ["id-company-1"]

    def test_without_pool_uses_random_hashes(self):
        entity = generate_random_entity("Directorship")
        props = entity.to_dict()["properties"]
        # Without a pool, entity-type props get random sha1 values (40 hex chars)
        for key in ("director", "organization"):
            if key in props:
                assert len(props[key][0]) == 40

    def test_associate_links_persons(self):
        pool = {"Person": ["id-a", "id-b"]}
        entity = generate_random_entity("Associate", entity_pool=pool)
        props = entity.to_dict()["properties"]
        assert props["person"][0] in ("id-a", "id-b")
        assert props["associate"][0] in ("id-a", "id-b")


# ---------------------------------------------------------------------------
# entity subcommand --connected flag
# ---------------------------------------------------------------------------


class TestConnectedCLI:
    def test_basic_connected_output(self):
        result = runner.invoke(
            cli,
            [
                "connected",
                "--schema",
                "Person",
                "--schema",
                "Company",
                "--schema",
                "Directorship",
            ],
        )
        assert result.exit_code == 0
        entities = parse_output(result)
        # --count defaults to 1, so 1 entity total
        assert len(entities) == 1

    def test_connected_with_count(self):
        result = runner.invoke(
            cli,
            [
                "connected",
                "--schema",
                "Person",
                "--schema",
                "Company",
                "--schema",
                "Directorship",
                "--count",
                "9",
            ],
        )
        assert result.exit_code == 0
        entities = parse_output(result)
        # --count 9 with 3 schemas = 3 per schema
        assert len(entities) == 9
        schemas = [e["schema"] for e in entities]
        assert schemas.count("Person") == 3
        assert schemas.count("Company") == 3
        assert schemas.count("Directorship") == 3

    def test_edge_entities_reference_node_ids(self):
        result = runner.invoke(
            cli,
            [
                "connected",
                "--schema",
                "Person",
                "--schema",
                "Company",
                "--schema",
                "Directorship",
                "--count",
                "5",
            ],
        )
        assert result.exit_code == 0
        entities = parse_output(result)

        node_ids = {e["id"] for e in entities if e["schema"] in ("Person", "Company")}
        company_ids = {e["id"] for e in entities if e["schema"] == "Company"}

        for e in entities:
            if e["schema"] == "Directorship":
                props = e["properties"]
                # director must reference a node from the pool
                assert props["director"][0] in node_ids
                # organization must reference a Company (only Organization subtype in pool)
                assert props["organization"][0] in company_ids

    def test_associate_references_persons(self):
        result = runner.invoke(
            cli,
            [
                "connected",
                "--schema",
                "Person",
                "--schema",
                "Associate",
                "--count",
                "3",
            ],
        )
        assert result.exit_code == 0
        entities = parse_output(result)

        person_ids = {e["id"] for e in entities if e["schema"] == "Person"}
        for e in entities:
            if e["schema"] == "Associate":
                props = e["properties"]
                assert props["person"][0] in person_ids
                assert props["associate"][0] in person_ids

    def test_nodes_emitted_before_edges(self):
        result = runner.invoke(
            cli,
            [
                "connected",
                "--schema",
                "Person",
                "--schema",
                "Directorship",
                "--schema",
                "Company",
                "--count",
                "6",
            ],
        )
        assert result.exit_code == 0
        entities = parse_output(result)
        # --count 6 with 3 schemas = 2 per schema
        assert len(entities) == 6
        schemas = [e["schema"] for e in entities]
        # All node schemas should appear before any edge schema
        last_node_idx = max(
            i for i, s in enumerate(schemas) if s in ("Person", "Company")
        )
        first_edge_idx = min(i for i, s in enumerate(schemas) if s == "Directorship")
        assert last_node_idx < first_edge_idx

    def test_error_no_edge_schema(self):
        result = runner.invoke(
            cli,
            ["connected", "--schema", "Person", "--schema", "Company"],
        )
        assert result.exit_code != 0
        assert "edge schema" in result.output

    def test_error_no_node_schema(self):
        result = runner.invoke(
            cli,
            ["connected", "--schema", "Directorship"],
        )
        assert result.exit_code != 0
        assert "non-edge schema" in result.output

    def test_multiple_edge_schemas(self):
        result = runner.invoke(
            cli,
            [
                "connected",
                "--schema",
                "Person",
                "--schema",
                "Company",
                "--schema",
                "Directorship",
                "--schema",
                "Ownership",
                "--count",
                "8",
            ],
        )
        assert result.exit_code == 0
        entities = parse_output(result)
        schemas = [e["schema"] for e in entities]
        # --count 8 with 4 schemas = 2 per schema
        assert len(entities) == 8
        assert schemas.count("Person") == 2
        assert schemas.count("Company") == 2
        assert schemas.count("Directorship") == 2
        assert schemas.count("Ownership") == 2

    def test_without_connected_flag_unchanged(self):
        result = runner.invoke(
            cli,
            ["entities", "--schema", "Person", "--count", "3"],
        )
        assert result.exit_code == 0
        entities = parse_output(result)
        assert len(entities) == 3
        assert all(e["schema"] == "Person" for e in entities)


# ---------------------------------------------------------------------------
# list subcommand
# ---------------------------------------------------------------------------


class TestListSchemata:
    def test_list_exits_cleanly(self):
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0

    def test_list_contains_header(self):
        result = runner.invoke(cli, ["list"])
        assert "Schema" in result.output
        assert "Type" in result.output
        assert "Description" in result.output

    def test_list_includes_known_node_schema(self):
        result = runner.invoke(cli, ["list"])
        lines = result.output.splitlines()
        person_lines = [line for line in lines if line.startswith("Person")]
        assert len(person_lines) == 1
        assert "node" in person_lines[0]

    def test_list_includes_known_edge_schema(self):
        result = runner.invoke(cli, ["list"])
        lines = result.output.splitlines()
        directorship_lines = [line for line in lines if line.startswith("Directorship")]
        assert len(directorship_lines) == 1
        assert "edge" in directorship_lines[0]

    def test_list_produces_no_entities(self):
        result = runner.invoke(cli, ["list"])
        # Output should not be valid JSONL (no entity lines)
        for line in result.output.splitlines():
            assert not line.startswith("{")


# ---------------------------------------------------------------------------
# entity subcommand --count-per-schema
# ---------------------------------------------------------------------------


class TestCountPerSchema:
    def test_single_schema(self):
        result = runner.invoke(
            cli,
            ["entities", "--schema", "Person", "--count-per-schema", "3"],
        )
        assert result.exit_code == 0
        entities = parse_output(result)
        assert len(entities) == 3
        assert all(e["schema"] == "Person" for e in entities)

    def test_multiple_schemas(self):
        result = runner.invoke(
            cli,
            [
                "entities",
                "--schema",
                "Person",
                "--schema",
                "Company",
                "--count-per-schema",
                "4",
            ],
        )
        assert result.exit_code == 0
        entities = parse_output(result)
        assert len(entities) == 8
        schemas = [e["schema"] for e in entities]
        assert schemas.count("Person") == 4
        assert schemas.count("Company") == 4

    def test_connected_with_count_per_schema(self):
        result = runner.invoke(
            cli,
            [
                "connected",
                "--schema",
                "Person",
                "--schema",
                "Company",
                "--schema",
                "Directorship",
                "--count-per-schema",
                "2",
            ],
        )
        assert result.exit_code == 0
        entities = parse_output(result)
        assert len(entities) == 6
        schemas = [e["schema"] for e in entities]
        assert schemas.count("Person") == 2
        assert schemas.count("Company") == 2
        assert schemas.count("Directorship") == 2

    def test_error_with_random_schema(self):
        result = runner.invoke(
            cli,
            ["entities", "--random-schema", "--count-per-schema", "5"],
        )
        assert result.exit_code != 0
        assert "--count-per-schema" in result.output


# ---------------------------------------------------------------------------
# entity subcommand --random-schema
# ---------------------------------------------------------------------------


class TestRandomSchema:
    ABSTRACT_SCHEMAS = {"Thing", "Analyzable", "Value", "Interval", "Interest"}

    def test_random_schema_excludes_abstract(self):
        result = runner.invoke(
            cli,
            ["entities", "--random-schema", "--count", "200"],
        )
        assert result.exit_code == 0
        entities = parse_output(result)
        assert len(entities) == 200
        schemas_used = {e["schema"] for e in entities}
        assert schemas_used.isdisjoint(self.ABSTRACT_SCHEMAS)
