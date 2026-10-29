"""Local administrative commands. No user credentials are stored in source files."""

import re

import click
from argon2 import PasswordHasher
from sqlalchemy import select

from .extensions import db
from .models import User

USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


def register_commands(app) -> None:
    @app.cli.command("create-user")
    @click.argument("username")
    @click.option(
        "--role", type=click.Choice(["analyst", "viewer"]), default="analyst", show_default=True
    )
    def create_user(username: str, role: str) -> None:
        """Create a local analyst or read-only viewer account interactively."""
        normalized_username = username.strip().lower()
        if not USERNAME_PATTERN.fullmatch(normalized_username):
            raise click.ClickException(
                "Username must be 3 to 64 lowercase letters, digits, dots, underscores, or hyphens."
            )
        existing = db.session.scalar(select(User.id).where(User.username == normalized_username))
        if existing is not None:
            raise click.ClickException("That username already exists.")

        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        if len(password) < 12 or len(password) > 128:
            raise click.ClickException("Password must be 12 to 128 characters.")
        user = User(
            username=normalized_username,
            password_hash=PasswordHasher().hash(password),
            role=role,
            is_active=True,
        )
        db.session.add(user)
        try:
            db.session.commit()
        except Exception as error:
            db.session.rollback()
            raise click.ClickException("The user could not be created.") from error
        click.echo(f"Created {role} account: {normalized_username}")
