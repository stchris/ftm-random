import click
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class Email:
    def __init__(
        self,
        subject: str,
        body: str,
        sender: str,
        recipient: str,
        date: str,
        in_reply_to: Optional[str] = None,
    ):
        self.subject = subject
        self.body = body
        self.sender = sender
        self.recipient = recipient
        self.date = date
        self.in_reply_to = in_reply_to

    def to_dict(self) -> Dict:
        return {
            "schema": "Email",
            "properties": {
                "subject": [self.subject],
                "body": [self.body],
                "sender": [self.sender],
                "recipient": [self.recipient],
                "date": [self.date],
                **({"inReplyTo": [self.in_reply_to]} if self.in_reply_to else {}),
            },
        }


class Person:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def to_dict(self) -> Dict:
        return {
            "schema": "Person",
            "properties": {
                "name": [self.name],
                "email": [self.email],
            },
        }


def generate_random_name() -> str:
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack"]
    last_names = ["Smith", "Doe", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"


def generate_random_email(name: str) -> str:
    return f"{name.lower().replace(' ', '.')}@example.com"


def generate_inbox(owner_name: Optional[str] = None, num_emails: int = 50) -> List[Dict]:
    owner_name = owner_name or generate_random_name()
    owner_email = generate_random_email(owner_name)
    owner = Person(owner_name, owner_email)
    circle = [Person(generate_random_name(), generate_random_email(generate_random_name())) for _ in range(10)]

    emails = []
    for i in range(num_emails):
        is_reply = random.random() < 0.75
        subject = f"Re: Meeting" if is_reply else f"Meeting {i}"
        body = f"Email body for {subject}"
        sender = random.choice([owner, *circle])
        recipient = random.choice([p for p in [owner, *circle] if p != sender])
        date = (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
        in_reply_to = emails[-1]["properties"]["subject"][0] if is_reply and emails else None

        email = Email(
            subject=subject,
            body=body,
            sender=sender.email,
            recipient=recipient.email,
            date=date,
            in_reply_to=in_reply_to,
        )
        emails.append(email.to_dict())

    entities = [owner.to_dict(), *[p.to_dict() for p in circle], *emails]
    return entities


@click.command()
@click.option("--owner", default=None, help="Name of the inbox owner.")
@click.option("--num-emails", default=50, help="Number of emails to generate.")
@click.option("--outfile", default=None, help="JSONL output file.")
def generate_inbox_command(owner: str, num_emails: int, outfile: str):
    entities = generate_inbox(owner, num_emails)
    if outfile:
        with open(outfile, "w") as f:
            for entity in entities:
                f.write(json.dumps(entity) + "\n")
    else:
        for entity in entities:
            print(json.dumps(entity))