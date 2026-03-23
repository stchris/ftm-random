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


@click.group()
def cli():
    """Generate random followthemoney entities."""


@cli.command()
@click.option("--count", default=1, help="Number of entities to generate.")
@click.option(
    "--count-per-schema",
    "count_per_schema",
    default=None,
    type=int,
    help="Number of entities to generate per schema (overrides --count).",
)
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
    "--outfile",
    "outfile",
    default=None,
    help="JSONL output file (leave this out for STDOUT)",
)
def entities(count, count_per_schema, schemata, random_schema, outfile):
    """Generate random followthemoney entities."""
    if count_per_schema is not None and random_schema:
        raise click.ClickException(
            "--count-per-schema cannot be used with --random-schema."
        )

    if random_schema:
        choices = [
            name for name, schema in model.schemata.items() if not schema.abstract
        ]
    else:
        choices = list(schemata)

    if count_per_schema is not None:
        for schema_name in choices:
            for _ in range(count_per_schema):
                ent = generate_random_entity(schema_name)
                click.echo(message=json.dumps(ent.to_dict()), file=outfile)
    else:
        for _ in range(count):
            ent = generate_random_entity(random.choice(choices))
            click.echo(message=json.dumps(ent.to_dict()), file=outfile)


@cli.command()
@click.option("--count", default=1, help="Number of entities to generate.")
@click.option(
    "--count-per-schema",
    "count_per_schema",
    default=None,
    type=int,
    help="Number of entities to generate per schema (overrides --count).",
)
@click.option(
    "--schema",
    "schemata",
    default=("Person", "Directorship"),
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
    "--outfile",
    "outfile",
    default=None,
    help="JSONL output file (leave this out for STDOUT)",
)
def connected(count, count_per_schema, schemata, random_schema, outfile):
    """Generate connected random followthemoney entities.

    Link edge entities (e.g. Directorship) to other generated entities.
    """
    if count_per_schema is not None and random_schema:
        raise click.ClickException(
            "--count-per-schema cannot be used with --random-schema."
        )

    if random_schema:
        choices = [
            name for name, schema in model.schemata.items() if not schema.abstract
        ]
    else:
        choices = list(schemata)

    # Separate node and edge schemata, generate nodes first,
    # then wire edge entities to real node IDs.
    node_schemata = []
    edge_schemata = []
    for name in choices:
        schema = model.get(name)
        if schema is None:
            raise click.ClickException(f"Unknown schema: {name}")
        if schema.edge:
            edge_schemata.append(name)
        else:
            node_schemata.append(name)

    if not edge_schemata:
        raise click.ClickException(
            "connected requires at least one edge schema "
            "(e.g. Directorship, Ownership, Associate)."
        )
    if not node_schemata:
        raise click.ClickException(
            "connected requires at least one non-edge schema (e.g. Person, Company)."
        )

    # Determine per-schema counts.
    all_schemata = node_schemata + edge_schemata
    if count_per_schema is not None:
        schema_counts = {name: count_per_schema for name in all_schemata}
    else:
        # Distribute count across all schemata (nodes first, then edges).
        num_schemata = len(all_schemata)
        base, remainder = divmod(count, num_schemata)
        schema_counts = {name: base for name in all_schemata}
        for i in range(remainder):
            schema_counts[all_schemata[i]] += 1

    # Generate node entities and collect their IDs by schema
    entity_pool = defaultdict(list)
    for schema_name in node_schemata:
        for _ in range(schema_counts[schema_name]):
            ent = generate_random_entity(schema_name)
            entity_pool[schema_name].append(ent.id)
            click.echo(message=json.dumps(ent.to_dict()), file=outfile)

    # Generate edge entities wired to the node pool
    for schema_name in edge_schemata:
        for _ in range(schema_counts[schema_name]):
            ent = generate_random_entity(schema_name, entity_pool=entity_pool)
            click.echo(message=json.dumps(ent.to_dict()), file=outfile)


@cli.command()
@click.option("--count", default=10, help="Number of Email entities to generate.")
@click.option(
    "--contacts",
    default=10,
    help="Number of contact Person entities.",
)
@click.option(
    "--outfile",
    "outfile",
    default=None,
    help="JSONL output file (leave this out for STDOUT)",
)
def inbox(count, contacts, outfile):
    """Generate a realistic email inbox for one Person entity.

    Generates one owner Person, a set of contact Persons, and Email entities
    where the owner appears in the From, To, or Cc field of every email.
    """
    # Generate the owner Person with a fixed email address
    owner = generate_random_entity("Person")
    owner_email = fake.email()
    click.echo(message=json.dumps(owner.to_dict()), file=outfile)

    # Generate contact Persons with email addresses
    contact_emails = []
    for _ in range(contacts):
        contact = generate_random_entity("Person")
        contact_emails.append((contact, fake.email()))
        click.echo(message=json.dumps(contact.to_dict()), file=outfile)

    if not contact_emails:
        raise click.ClickException("Need at least one contact to generate emails.")

    emails_only = [e for _, e in contact_emails]

    # Generate Email entities
    for _ in range(count):
        email_entity = model.make_entity("Email")

        # Subject with reply/forward probabilities
        base_subject = fake.sentence(nb_words=random.randint(3, 8)).rstrip(".")
        r = random.random()
        if r < 0.70:
            subject = f"Re: {base_subject}"
        elif r < 0.85:
            subject = f"Fwd: {base_subject}"
        else:
            subject = base_subject
        email_entity.add("subject", subject)

        email_entity.add(
            "date", fake.date_between(start_date="-5y", end_date="today").isoformat()
        )
        email_entity.add("bodyText", fake.paragraph())

        # Owner appears in From, To, or Cc of every email
        owner_role = random.choice(["from", "to", "cc"])
        email_entity.add(owner_role, owner_email)

        # 75%: between two entities; 25%: more participants
        if random.random() < 0.75:
            other = random.choice(emails_only)
            if owner_role == "from":
                email_entity.add("to", other)
            elif owner_role == "to":
                email_entity.add("from", other)
            else:  # cc: need someone in both from and to
                other2 = random.choice(emails_only)
                email_entity.add("from", other)
                email_entity.add("to", other2)
        else:
            num_others = random.randint(2, min(5, len(emails_only)))
            others = random.sample(emails_only, num_others)
            assigned_from = owner_role == "from"
            assigned_to = owner_role == "to"
            for addr in others:
                if not assigned_from:
                    email_entity.add("from", addr)
                    assigned_from = True
                elif not assigned_to:
                    email_entity.add("to", addr)
                    assigned_to = True
                else:
                    email_entity.add(random.choice(["to", "cc"]), addr)

        email_entity.make_id(fake.uuid4())
        click.echo(message=json.dumps(email_entity.to_dict()), file=outfile)


@cli.command(name="list")
def list_schemata():
    """List all available FTM schemata with their type and description."""
    col_name = 20
    col_type = 6
    header = f"{'Schema':<{col_name}}  {'Type':<{col_type}}  Description"
    click.echo(header)
    click.echo("-" * len(header))
    for name, schema in sorted(model.schemata.items()):
        entity_type = "edge" if schema.edge else "node"
        description = schema.description or ""
        click.echo(f"{name:<{col_name}}  {entity_type:<{col_type}}  {description}")


if __name__ == "__main__":
    cli()
