"""
Shared utilites for MV Polar Bears project
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from numpy import nan
import pandas as pd

# constants
DOC_TITLE = 'MV Polar Bears'
SHEET_TITLE = 'Debug'


def get_client(key_file):
    """
    Return interfaces to Google Sheets data store
    
    Arguments:
        key_file: Google Sheets / Drive API secret key file
    
    Returns:
        client: gspread.client.Client
        doc: gspread.models.Spreadsheet
        sheet: gspread.models.Worksheet
    """
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(key_file, scope)
    client = gspread.authorize(creds)
    doc = client.open(DOC_TITLE)
    sheet = doc.worksheet(SHEET_TITLE)
    return client, doc, sheet


def read_sheet(sheet):
    """
    Read current data from Google Sheets

    Arguments:
        sheet: gspread sheet, connected

    Return: pd dataframe containing current data
    """
    content = sheet.get_all_records(default_blank=nan)
    content = pd.DataFrame(content)
    return content

