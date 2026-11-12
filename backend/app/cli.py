"""Operational commands.

python -m app.cli sync-catalogue
python -m app.cli create-director --email EMAIL --name "NAME"   (password prompted)
python -m app.cli seed-dev-users          (APP_ENV=development only)
python -m app.cli verify-audit-chain
"""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Environment, get_settings
from app.db.session import get_session_factory
from app.platform.audit import service as audit
from app.platform.authz.catalogue import ROLES
from app.platform.authz.sync import sync_catalogue
from app.platform.identity import service as identity
from app.platform.identity.models import Role, User, UserMfa
from app.platform.security import crypto, tokens, totp

DEV_DOMAIN = "dev.aven.invalid"  # .invalid can never receive email (RFC 2606)


def _db() -> Session:
    return get_session_factory()()


def cmd_sync_catalogue(_: argparse.Namespace) -> int:
    with _db() as db:
        sync_catalogue(db)
    print("Catalogue synchronised.")
    return 0


def cmd_create_director(args: argparse.Namespace) -> int:
    with _db() as db:
        sync_catalogue(db)
        director_role = db.execute(select(Role).where(Role.code == "director")).scalar_one()
        if db.execute(select(User.id).where(User.role_id == director_role.id)).first():
            print("A Director account already exists. Refusing to create another.", file=sys.stderr)
            return 2
        password = sys.stdin.readline().rstrip("\n") if args.password_stdin else ""
        if not password:
            password = getpass.getpass("Director password: ")
            if password != getpass.getpass("Repeat password: "):
                print("Passwords do not match.", file=sys.stderr)
                return 2
        user = identity.create_user(
            db,
            email=args.email,
            display_name=args.name,
            role_code="director",
            created_by=None,
            status="active",
        )
        identity.set_password(db, user, password)
        db.commit()
    print(
        f"Director account created for {args.email}. Two-factor setup is required at first sign-in."
    )
    return 0


def cmd_seed_dev_users(_: argparse.Namespace) -> int:
    if get_settings().app_env is not Environment.DEVELOPMENT:
        print("Refusing: seed-dev-users only runs with APP_ENV=development.", file=sys.stderr)
        return 2
    with _db() as db:
        sync_catalogue(db)
        print("DEVELOPMENT-ONLY TEST ACCOUNTS (not real people). Shown once.\n")
        for role in ROLES:
            email = f"{role.code.replace('_', '-')}@{DEV_DOMAIN}"
            if db.execute(select(User.id).where(User.email == email)).first():
                print(f"  {email:45} already exists")
                continue
            password = f"Dev-{tokens.new_token(9)}"
            user = identity.create_user(
                db,
                email=email,
                display_name=f"DEV-ONLY {role.name}",
                role_code=role.code,
                created_by=None,
                is_dev_account=True,
                status="active",
            )
            identity.set_password(db, user, password)
            line = f"  {email:45} password: {password}"
            if role.mfa_required:
                secret = totp.new_secret()
                db.add(
                    UserMfa(
                        user_id=user.id,
                        secret_encrypted=crypto.encrypt(secret),
                        enabled_at=identity.now(),
                    )
                )
                line += f"  TOTP secret: {secret}"
            print(line)
        db.commit()
    return 0


def cmd_verify_audit_chain(_: argparse.Namespace) -> int:
    with _db() as db:
        report = audit.verify_chain(db)
    print(f"ok={report.ok} events_checked={report.events_checked}")
    if report.first_bad_seq is not None:
        print(f"first_bad_seq={report.first_bad_seq}")
    return 0 if report.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sync-catalogue").set_defaults(func=cmd_sync_catalogue)
    p = sub.add_parser("create-director")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--password-stdin", action="store_true")
    p.set_defaults(func=cmd_create_director)
    sub.add_parser("seed-dev-users").set_defaults(func=cmd_seed_dev_users)
    sub.add_parser("verify-audit-chain").set_defaults(func=cmd_verify_audit_chain)
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
