import json
import random
import warnings
from collections import defaultdict

import click
from faker import Faker

# Suppress the warning message from requests, which is very cautious with
# newer versions of urllib3 and chardet. Must be set before importing
# anything that pulls in requests.
warnings.filterwarnings("ignore", message="urllib3", module="requests")

from followthemoney import model  # noqa: E402

fake = Faker()

# Generators for each FTM property type
TYPE_GENERATORS = {
    "name": lambda: fake.name(),
    "string": lambda: fake.word(),
    "date": lambda: fake.date_between(start_date="-80y", end_date="today").isoformat(),
    "country": lambda: fake.country_code().lower(),
    "identifier": lambda: fake.bothify("???-########"),
    "gender": lambda: random.choice(["male", "female", "other"]),
    "number": lambda: str(random.randint(1, 999)),
    "language": lambda: fake.language_code(),
    "email": lambda: fake.email(),
    "phone": lambda: fake.phone_number(),
    "url": lambda: fake.url(),
    "address": lambda: fake.address().replace("\n", ", "),
    "text": lambda: fake.sentence(),
    "topic": lambda: random.choice(
        ["role.pep", "role.rca", "sanction", "crime", "fin.bank"]
    ),
    "entity": lambda: fake.sha1(),
}

# Properties to skip (internal-use fields)
SKIP_PROPERTIES = {"indexText"}


def _pick_entity_id(prop, entity_pool):
    """Pick a random entity ID from the pool that matches the property's range."""
    range_schema = prop.range
    if range_schema is None:
        return None
    candidates = []
    for schema_name, ids in entity_pool.items():
        schema = model.get(schema_name)
        if schema is not None and schema.is_a(range_schema):
            candidates.extend(ids)
    if candidates:
        return random.choice(candidates)
    return None


def generate_random_entity(schema_name, entity_pool=None):
    schema = model.get(schema_name)
    if schema is None:
        raise click.ClickException(f"Unknown schema: {schema_name}")

    entity = model.make_entity(schema_name)

    settable = [
        p
        for p in schema.properties.values()
        if not p.stub and p.name not in SKIP_PROPERTIES
    ]

    for prop in settable:
        is_required = prop.name in schema.required
        type_name = prop.type.name

        # For entity-type properties in connected mode, wire to real entities
        if type_name == "entity" and entity_pool is not None:
            entity_id = _pick_entity_id(prop, entity_pool)
            if entity_id is not None:
                entity.add(prop, entity_id)
            continue

        # Always set name-type and required properties
        if type_name == "name" or is_required:
            gen = TYPE_GENERATORS.get(type_name)
            if gen:
                entity.add(prop, gen())
            continue

        # Set other properties with some probability
        if random.random() < 0.4:
            gen = TYPE_GENERATORS.get(type_name)
            if gen:
                entity.add(prop, gen())

    entity.make_id(fake.uuid4())
    schema.validate(entity.to_dict())
    return entity


@click.command()
@click.option("--count", default=1, help="Number of entities to generate.")
@click.option(
    "--schema",
    "schemata",
    default=("Person",),
    multiple=True,
    help="FTM schema name (can be specified multiple times).",
)
@click.option(
    "--random-schema",
    is_flag=True,
    default=False,
    help="Use a random schema for each entity.",
)
@click.option(
    "--connected",
    is_flag=True,
    default=False,
    help="Link edge entities (e.g. Directorship) to other generated entities.",
)
@click.option(
    "--outfile",
    "outfile",
    default=None,
    help="JSONL output file (leave this out for STDOUT)",
)
@click.option(
    "--list",
    "list_schemata",
    is_flag=True,
    default=False,
    help="List all available FTM schemas with their type and description.",
)
def generate_entities(
    count, schemata, random_schema, connected, outfile, list_schemata
):
    """Generate random followthemoney entities."""
    if list_schemata:
        col_name = 20
        col_type = 6
        header = f"{'Schema':<{col_name}}  {'Type':<{col_type}}  Description"
        click.echo(header)
        click.echo("-" * len(header))
        for name, schema in sorted(model.schemata.items()):
            entity_type = "edge" if schema.edge else "node"
            description = schema.description or ""
            click.echo(f"{name:<{col_name}}  {entity_type:<{col_type}}  {description}")
        return

    if random_schema:
        choices = list(model.schemata.keys())
    else:
        choices = list(schemata)

    if not connected:
        for _ in range(count):
            entity = generate_random_entity(random.choice(choices))
            click.echo(message=json.dumps(entity.to_dict()), file=outfile)
        return

    # Connected mode: separate node and edge schemas, generate nodes first,
    # then wire edge entities to real node IDs.
    node_schemas = []
    edge_schemas = []
    for name in choices:
        schema = model.get(name)
        if schema is None:
            raise click.ClickException(f"Unknown schema: {name}")
        if schema.edge:
            edge_schemas.append(name)
        else:
            node_schemas.append(name)

    if not edge_schemas:
        raise click.ClickException(
            "--connected requires at least one edge schema "
            "(e.g. Directorship, Ownership, Associate)."
        )
    if not node_schemas:
        raise click.ClickException(
            "--connected requires at least one non-edge schema (e.g. Person, Company)."
        )

    # Distribute count across all schemas (nodes first, then edges).
    all_schemas = node_schemas + edge_schemas
    num_schemas = len(all_schemas)
    base, remainder = divmod(count, num_schemas)
    schema_counts = {name: base for name in all_schemas}
    for i in range(remainder):
        schema_counts[all_schemas[i]] += 1

    # Generate node entities and collect their IDs by schema
    entity_pool = defaultdict(list)
    for schema_name in node_schemas:
        for _ in range(schema_counts[schema_name]):
            entity = generate_random_entity(schema_name)
            entity_pool[schema_name].append(entity.id)
            click.echo(message=json.dumps(entity.to_dict()), file=outfile)

    # Generate edge entities wired to the node pool
    for schema_name in edge_schemas:
        for _ in range(schema_counts[schema_name]):
            entity = generate_random_entity(schema_name, entity_pool=entity_pool)
            click.echo(message=json.dumps(entity.to_dict()), file=outfile)


if __name__ == "__main__":
    generate_entities()
