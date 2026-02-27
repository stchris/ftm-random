import json
import random

import click
from faker import Faker
from followthemoney import model

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
    "topic": lambda: random.choice(["role.pep", "role.rca", "sanction", "crime", "fin.bank"]),
    "entity": lambda: fake.sha1(),
}

# Properties to skip (internal-use fields)
SKIP_PROPERTIES = {"indexText"}


def generate_random_entity(schema_name):
    schema = model.get(schema_name)
    if schema is None:
        raise click.ClickException(f"Unknown schema: {schema_name}")

    entity = model.make_entity(schema_name)

    settable = [
        p for p in schema.properties.values()
        if not p.stub and p.name not in SKIP_PROPERTIES
    ]

    for prop in settable:
        is_required = prop.name in schema.required
        type_name = prop.type.name

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
@click.option("--schema", "schemata", default=("Person",), multiple=True, help="FTM schema name (can be specified multiple times).")
@click.option("--random-schema", is_flag=True, default=False, help="Use a random schema for each entity.")
@click.option("--outfile", "outfile", default=None, help="JSONL output file or '-' for STDOUT" )
def generate_entities(count, schemata, random_schema, outfile):
    """Generate random followthemoney entities."""
    if random_schema:
        choices = list(model.schemata.keys())
    else:
        choices = list(schemata)
    for _ in range(count):
        entity = generate_random_entity(random.choice(choices))
        click.echo(message=json.dumps(entity.to_dict()), file=outfile)


if __name__ == "__main__":
    generate_entities()
