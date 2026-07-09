from __future__ import annotations

from pathlib import Path

from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import logging

# Todo: Non-repo storage 
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = PROJECT_ROOT / "secrets"
CREDENTIALS_PATH = SECRETS_DIR / "credentials.json"
TOKEN_PATH = SECRETS_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

logger = logging.getLogger(__name__)
logger.setLevel('INFO')

def load_credentials(token_path: str | Path = TOKEN_PATH, scopes: list[str] = SCOPES) -> UserCredentials:
    '''
    Loads Google credentials from a token file. Refreshes the token if it is expired.
    Raises an error if the credentials are invalid.
    '''
    token_path = Path(token_path)
    
    creds = UserCredentials.from_authorized_user_file(str(token_path), scopes=scopes)

    if not creds.has_scopes(scopes):
        raise RuntimeError(
            "Google credentials are missing required OAuth scopes. "
            f"Required scopes: {scopes}. Delete/regenerate {token_path} "
            "or rerun setup_token so Google asks for consent again."
        )

    if creds.expired and creds.refresh_token:
        logger.warning("Google UserCredentials are expired. Attempting to refresh...")
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
        logger.info("Success!")

    if not creds.valid:
        raise RuntimeError("Google credentials are invalid and could not be refreshed.")

    return creds


def get_user_credentials(
    credentials_path: str | Path = CREDENTIALS_PATH,
    token_path: str | Path = TOKEN_PATH,
    scopes: list[str] = SCOPES,
) -> UserCredentials:
    """
    Returns Google OAuth credentials for an individual user.
    
    Requirements:
        credentials_path file must exist and user must have access to the respective Google Cloud Client

    First run:
        Opens browser for Google login + consent.

    Later runs:
        Reuses token.json and refreshes it when needed.
    """
    credentials_path = Path(credentials_path)
    token_path = Path(token_path)
    token_path.parent.mkdir(parents=True, exist_ok=True)

    creds = None

    if token_path.exists():
        creds = load_credentials(token_path, scopes)
        # creds = UserCredentials.from_authorized_user_file(
        #     str(token_path),
        #     scopes=scopes,
        # )

    if creds and not creds.has_scopes(scopes):
        logger.warning('Creds exist, but do not have necessary scopes. Resetting to null')
        creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path),
                scopes=scopes,
            )

            creds = flow.run_local_server(port=0, prompt="consent")

        token_path.write_text(creds.to_json())

    return creds
