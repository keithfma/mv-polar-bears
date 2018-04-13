"""
Scratch space for developing key functions before it is clear where they will
live in the final package
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas
from numpy import nan


# constants
# TODO: move to a config file
KEY_FILE = 'secret.json'
DOC_TITLE = 'MV Polar Bears Attendence'
SHEET_TITLE = 'Data'


def sheets_get_client(key_file):
    """Return authenticated client for Google Sheets"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(key_file, scope)
    client = gspread.authorize(creds)
    return client


def sheets_read_data():
    """
    Read attendence data from Google Sheets

    Return: pandas dataframe containing current data
    """
    client = sheets_get_client(KEY_FILE)
    doc = client.open(DOC_TITLE)
    sheet = doc.worksheet(SHEET_TITLE)
    content = sheet.get_all_records(default_blank=nan)
    return pandas.DataFrame(content)


def add_dates(data):
    """
    Convert year, month, day columns to datetime.date objects

    Return: Nothing, adds "DATE" column to dataframe
    """
    data['DATE'] = pandas.to_datetime(data[['YEAR', 'MONTH', 'DAY']]).dt.date


# DEBUG: try out a few things
if __name__ == '__main__':
    data = sheets_read_data()
    add_dates(data)

