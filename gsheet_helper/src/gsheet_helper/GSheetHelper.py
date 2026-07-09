from .utils import gsheets 
from .utils import credentials
import pandas as pd
from pathlib import Path
from googleapiclient.discovery import build

import logging

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class GSheetHelper:
    def __init__(self, url=None, spreadsheet_id=None):
        if spreadsheet_id is None:
            spreadsheet_id = gsheets.extract_spreadsheet_id(url)
        self.spreadsheet_id = spreadsheet_id
        self.scopes = credentials.SCOPES
        self.token_path = Path(credentials.TOKEN_PATH)
        self.creds = credentials.get_user_credentials(token_path=self.token_path, scopes=self.scopes)
        self.sheets_service = build("sheets", "v4", credentials=self.creds)
        self.drive_service = build("drive", "v3", credentials=self.creds)
        self._properties = None
    
    def _fetch_properties(self):
        properties = (self.sheets_service
                           .spreadsheets()
                           .get(
                               spreadsheetId=self.spreadsheet_id,\
                               fields="sheets.properties"
                               )
                           .execute()
                     )
        
        return properties
        
    @property
    def properties(self):
        if self._properties is None:
            self._properties = self._fetch_properties()
    
        return self._properties
                               
    @property
    def sheets(self):
        return [sheet['properties']['title'] for sheet in self.properties.get('sheets')]
    
    def share_spreadsheet(self, email, role, notify):
        gsheets.share_spreadsheet(
            drive_service=self.drive_service, 
            spreadsheet_id=self.spreadsheet_id, 
            email=email, 
            role=role, 
            notify=notify)
    
    def transfer_ownership(self, new_owner_email, internal_account=False):
        return gsheets.transfer_sheet_ownership(
            self.drive_service, 
            self.spreadsheet_id, 
            new_owner_email=new_owner_email, 
            internal_account=internal_account)

    def read_tab(self, tab_name, range_name=''):
        '''
        Reads a tab from a Google Sheets spreadsheet as a pandas dataframe.
        Args:
            tab_name: The name of the tab to read.
            range_name: The range of the tab to read.
        Returns:
            A pandas dataframe.
        '''
        if tab_name not in self.sheets:
            raise ValueError(f'tab name not found in worksheet. Received {tab_name}, elligible values include {sorted(self.sheets)}')
        
        df = gsheets.read_tab_as_df(
            sheets_service=self.sheets_service, 
            spreadsheet_id=self.spreadsheet_id, 
            tab_name=tab_name, 
            range_name=range_name)

        return df

    def clear_tab(self, tab_name: str):
        gsheets.clear_tab(self.sheets_service, self.spreadsheet_id, tab_name)

    def add_tab(self, tab_name: str):
        gsheets.add_tab(self.sheets_service, self.spreadsheet_id, tab_name)

    def write_dataframe_to_tab(
        self,
        df: pd.DataFrame,
        tab_name: str,
        null_intermediate_fill: int = -9999,
        null_external_fill: str = '', 
        clear_existing_tab: bool = True,
        create_if_missing: bool = True,
        range_name: str = 'A1',
        value_input_option: str = "RAW") -> None:
        '''
        Write a pandas dataframe to an existing tab, defaulting to position A1.
        Args:
            df: The dataframe to write.
            tab_name: The name of the tab to write to.
            clear_existing_tab: Whether to clear the existing tab.
            create_if_missing: Whether to create the tab if it is missing.
            range_name: The range of the tab to write to.
            include_index: Whether to include the index in the dataframe.
            value_input_option: The value input option.
        '''
        output_range = f"{gsheets.quote_tab_name(tab_name)}!{range_name}"
        
        
        if tab_name not in self.sheets:
            if not create_if_missing:
                raise ValueError(f'{tab_name} not found in existing tabs. If you want to create the tab, set `create_if_missing` to True.')
            
            self.add_tab(tab_name)
            # structural change to workbook means existing properties are stale
            self._properties = None

        if clear_existing_tab:
            gsheets.clear_tab(self.sheets_service, self.spreadsheet_id, tab_name)
        
        gsheets.write_to_tab(
            self.sheets_service, 
            self.spreadsheet_id,
            df,
            output_range,
            null_intermediate_fill=null_intermediate_fill,
            null_external_fill=null_external_fill,
            value_input_option=value_input_option,
            )

    @classmethod
    def create(cls, spreadsheet_name=None, first_tab_name="Sheet1"):
        '''
        Flexible method to when needing to simultaneously create a new Google Sheet reference it as a GSheetHelper class:

        e.g. 
        
        gsh = GSheetHelper.create(
            spreadsheet_name="Weekly KPI Report",
            first_tab_name="Summary",
        )
        '''
        creds = credentials.load_credentials(
            token_path=Path(gsheets.TOKEN_PATH),
            scopes=credentials.SCOPES,
        )
        sheets_service = build("sheets", "v4", credentials=creds)

        spreadsheet_id = gsheets.create_spreadsheet(
            sheets_service=sheets_service,
            spreadsheet_name=spreadsheet_name,
            first_tab_name=first_tab_name,
        )

        return cls(spreadsheet_id=spreadsheet_id)