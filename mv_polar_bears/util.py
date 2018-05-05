"""
Shared utilites for MV Polar Bears project
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from numpy import nan
import pandas as pd
import pytz
import dateutil
from pdb import set_trace

# constants
DOC_TITLE = 'MV Polar Bears'
SHEET_TITLE = 'Debug'
US_EASTERN = pytz.timezone('US/Eastern')


def parse_datetime(date_str, time_str):
    """Utility for parsing DATE and TIME columns to python datetime"""
    dt = dateutil.parser.parse(date_str + ' ' + time_str) 
    dt = dt.replace(tzinfo=US_EASTERN)
    return dt    


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
    Read current data from Google Sheets and do some post-processing

    Arguments:
        sheet: gspread sheet, connected

    Return: pd dataframe containing current data
    """
    # read sheet to dataframe
    content = sheet.get_all_records(default_blank=nan)
    content = pd.DataFrame(content)

    # set index to datetime
    dt_text = content['DATE'] + ' ' + content['TIME']
    content['DATETIME'] = dt_text.apply(
        lambda x: dateutil.parser.parse(x).replace(tzinfo=US_EASTERN))
    content.set_index('DATETIME', drop=True, inplace=True)

    return content

