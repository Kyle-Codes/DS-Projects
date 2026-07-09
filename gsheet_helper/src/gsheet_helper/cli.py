import argparse
import os

from .utils.credentials import CREDENTIALS_PATH, TOKEN_PATH, get_user_credentials

def setup_auth(args) -> None:
    get_user_credentials(
        credentials_path=args.credentials,
        token_path=args.token,
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="gsheet-helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser("setup-auth")
    setup_parser.add_argument("--credentials", default=CREDENTIALS_PATH)
    setup_parser.add_argument("--token", default=TOKEN_PATH)
    setup_parser.set_defaults(func=setup_auth)

    args = parser.parse_args()
    args.func(args)