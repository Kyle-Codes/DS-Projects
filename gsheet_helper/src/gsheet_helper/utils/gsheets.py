from __future__ import annotations

import re
import pandas as pd
import datetime

from googleapiclient.errors import HttpError
import logging

from pandas.core.dtypes.cast import dict_compat

logger = logging.getLogger(__name__)
logger.setLevel('INFO')

def quote_tab_name(tab_name: str) -> str:
    escaped = tab_name.replace("'", "''")
    return f"'{escaped}'"

def clear_tab(
    sheets_service, 
    spreadsheet_id: str, 
    tab_name: str) -> None:
    logger.info(f"Clearing tab {tab_name} in spreadsheet {spreadsheet_id}")
    (sheets_service
     .spreadsheets()
     .values()
     .clear(
         spreadsheetId=spreadsheet_id,
         range=quote_tab_name(tab_name),
         body={},
         )
     .execute())

def extract_tab_values(
    sheets_service,
    spreadsheet_id: str,
    tab_name: str, 
    range_name: str = "") -> dict:

    if range_name != '':
            range_name = '!' + range_name

    payload = (sheets_service
               .spreadsheets()
               .values()
               .get(spreadsheetId=spreadsheet_id, 
                    range=f'{quote_tab_name(tab_name)}{range_name}')
               .execute()
            )

    sheet_values = payload.get('values', []) 
    #TODO: Confirm if this actaully works as expected
    if len(sheet_values) == 0:
        logger.warning(f'No contents found in tab {tab_name}')
    
    return sheet_values


def read_tab_as_df(
    sheets_service, 
    spreadsheet_id: str, 
    tab_name: str, 
    range_name: str = "") -> pd.DataFrame:
    '''
    Reads a tab from a Google Sheets spreadsheet as a pandas dataframe.
    Args:
        sheets_service: The Google Sheets service object.
        spreadsheet_id: The ID of the spreadsheet.
        tab_name: The name of the tab to read.
        range_name: The range of the tab to read.
    Returns:
        A pandas dataframe.
    '''
    sheet_values = extract_tab_values(
        sheets_service=sheets_service,
        spreadsheet_id=spreadsheet_id,
        tab_name=tab_name,
        range_name=range_name)
    
    df = pd.DataFrame(data=sheet_values[1:], columns=sheet_values[0])

    return df


def add_tab(
    sheets_service,
    spreadsheet_id: str,
    tab_name: str,
    rows: int = 1000,
    cols: int = 26,
) -> int:
    """
    Add a new tab to an existing Google Sheets workbook.
    Returns the numeric sheetId of the new tab.
    """
    body = {
        "requests": [
            {
                "addSheet": {
                    "properties": {
                        "title": tab_name,
                        "gridProperties": {
                            "rowCount": rows,
                            "columnCount": cols,
                        },
                    }
                }
            }
        ]
    }

    response = (
        sheets_service
        .spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body,
        )
        .execute()
    )
    
    return response["replies"][0]["addSheet"]["properties"]["sheetId"]

def extract_spreadsheet_id(url: str) -> str:
    """
    Extract a Google Sheets spreadsheet ID from a URL.

    Example:
        https://docs.google.com/spreadsheets/d/1abcDEF123/edit#gid=0
        -> 1abcDEF123
    """
    pattern = r"/spreadsheets/d/([a-zA-Z0-9-_]+)"
    match = re.search(pattern, url)

    if not match:
        raise ValueError(f"Could not extract spreadsheet ID from URL: {url}")

    return match.group(1)

def write_to_tab(
    sheets_service, 
    spreadsheet_id: str, 
    df: pd.DataFrame,
    output_range: str,   
    null_intermediate_fill: int,
    null_external_fill: str = '',
    value_input_option: str = 'RAW'):

    risky_dtype_cols = df.select_dtypes(exclude=['number', 'str', 'bool']).columns
    if len(risky_dtype_cols) > 0:
        logger.warning(f'Some columns contain advanced datatypes. Confirm values in {risky_dtype_cols} properly converted to strings')
    # Some datatypes (e.g. timedeltas) require numeric inputs to fillna 
    if df.isin([null_intermediate_fill]).any(axis=None):
        raise ValueError(f'df already contains an instance of {null_intermediate_fill}. Select another input for `null_intermediate_fill`')
    
    tmp = df.fillna(null_intermediate_fill).astype(str).replace(str(null_intermediate_fill), null_external_fill)
    data = [tmp.columns.values.tolist()] + tmp.values.tolist()
    
    (
            sheets_service
            .spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=output_range,
                valueInputOption=value_input_option,
                body={"values": data},
            )
            .execute()
        )

def create_spreadsheet(
    sheets_service,
    spreadsheet_name: str = None,
    first_tab_name: str = 'Sheet1',
    ) -> str:
    '''
    Creates a new Google Sheets spreadsheet
    '''
    if spreadsheet_name is None:
        spreadsheet_name = f'New Spreadsheet: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

    body = {
        "properties": {"title": spreadsheet_name,},
        
        "sheets": [
            {
                "properties": {"title": first_tab_name,}
            }
        ],
    }

    logger.info('Creating new spreadsheet...')

    response = (
        sheets_service
        .spreadsheets()
        .create(
            body=body
        )
        .execute()
    )

    new_sheet_id = response["spreadsheetId"]
    logger.info(f'Success! Created new spreadsheet, id {new_sheet_id}.')

    return new_sheet_id

def share_spreadsheet(
    drive_service,
    spreadsheet_id: str,
    email: str,
    role: str = "reader",
    notify: bool = False
) -> dict:
    """
    Share a Google Sheets workbook with a user. Leverages drive API v3: 
    https://developers.google.com/workspace/drive/api/guides/manage-sharing

    This function is only intended to be used to share with a single email address at a time. 
    If sharing with multiple individuals is required, intended usage pattern is as follows:

            users = {'user1': 'role1', 'user2': 'role2'}
            
            for email, role in user.items():
                share_sheet(drive_service, spreadsheet_id, email, role)

    role options:
        reader: View only; cannot edit or comment
        commenter: View and add comments only
        writer: Edit permissions (Editor).
    """
    role = role.lower()
    if role not in ["reader", "commenter", "writer"]:
        raise ValueError(
            f"role must be one of reader, commenter, writer. Received: {role}"
        )

    permission = {
        "type": "user",
        "role": role,
        "emailAddress": email,
    }

    try:
        return (
            drive_service
            .permissions()
            .create(
                fileId=spreadsheet_id,
                body=permission,
                sendNotificationEmail=notify,
                supportsAllDrives=True,
            )
            .execute()
        )
    except HttpError as exc:
        if exc.resp.status == 404:
            raise FileNotFoundError(
                "Drive API could not find the spreadsheet. If Sheets API reads "
                "work but sharing fails, regenerate token.json with the Drive "
                "scope and confirm the authenticated account can share the file."
            ) from exc
        raise
    
def transfer_sheet_ownership(
    drive_service,
    spreadsheet_id: str,
    new_owner_email: str,
    internal_account: bool = False,
):
    if not isinstance(internal_account, bool):
        raise TypeError(f'internal_account must be a boolean value. \
            Received {internal_account}, type {type(internal_account)}')
    
    permissions = drive_service.permissions().list(
        fileId=spreadsheet_id,
        fields="permissions(id,emailAddress,role,pendingOwner)",
    ).execute()

    # find the first instance of a permission for the given email. 
    # As each email can only have one permission, 
    # no concern for duplicate entries being missed
    existing_permission = next(
        (
            p for p in permissions.get("permissions", [])
            if p.get("emailAddress", "").lower() == new_owner_email.lower()
        ),
        None,
    )

    if internal_account is True:
        body = {"role": "owner"}
        query = {"transferOwnership": True}
        email_message = 'You have been given ownership of the attached spreadsheet.'
    else: 
        body = {
            "role": "writer",
            "pendingOwner": True,
            }
        query = {}
        email_message = "Please accept ownership of this spreadsheet."

    if existing_permission is not None:
        logger.warning(f'''User already has spreadsheet access. Google API does not
            support emailing users with existing access to notify of ownership transfer.
            Please notify {new_owner_email} to make them aware of the ownership transfer request''')

        logger.info(f"Initiating transfer to {new_owner_email}...")

        msg = drive_service.permissions().update(
            fileId=spreadsheet_id,
            permissionId=existing_permission['id'],           
            supportsAllDrives=True,
            body=body,
             **query
        )
    
    else: 
        logger.info(f"User does not yet have spreadsheet access; creating new permission for {new_owner_email}.")
        body = {
            "type": "user",
            "role": "writer",
            "emailAddress": new_owner_email,
            "pendingOwner": True,
            }
        # query = {"transferOwnership": True}

        msg = drive_service.permissions().create(
                fileId=spreadsheet_id,
                sendNotificationEmail=True,
                emailMessage=email_message,
                supportsAllDrives=True,
                body=body,
                **query
            )
    
    try:
        payload = msg.execute()
        logger.info(f"Transfer successfully initiated.")
        logger.warning(f"Don't forget to notify {new_owner_email}.")
    except HttpError as exc:
        if exc.resp.status == 404:
            raise FileNotFoundError(
                "Drive API could not find the spreadsheet. If Sheets API reads "
                "work but sharing fails, regenerate token.json with the Drive "
                "scope and confirm the authenticated account can share the file."
            ) from exc
        raise
    return payload   