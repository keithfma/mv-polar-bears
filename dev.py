"""
Scratch space for developing key functions before it is clear where they will
live in the final package
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from numpy import nan
from matplotlib import pyplot as plt


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

    Return: pd dataframe containing current data
    """
    client = sheets_get_client(KEY_FILE)
    doc = client.open(DOC_TITLE)
    sheet = doc.worksheet(SHEET_TITLE)
    content = sheet.get_all_records(default_blank=nan)
    return pd.DataFrame(content)


def add_dates(data):
    """
    Convert year, month, day columns to datetime.date objects

    Return: Nothing, adds "DATE" column to dataframe
    """
    data['DATE'] = pd.to_datetime(data[['YEAR', 'MONTH', 'DAY']]).dt.date


def first_plot(data):
    """Display attendence vs time plot"""
    # constants
    clr_group = 'b'
    clr_newbies = 'g'

    # plot years independently
    label_group = 'Group'
    label_newbies = 'Newbies'
    years = data['YEAR'].unique()
    for year in years:
        year_data = data[data['YEAR'] == year]
        plt.plot(year_data['DATE'], year_data['GROUP'], color=clr_group, label=label_group)
        plt.plot(year_data['DATE'], year_data['NEWBIES'], color=clr_newbies, label=label_newbies)
        label_group = '_nolegend_'
        label_newbies = '_nolegend_'

    plt.ylim(ymin=0)
    plt.grid(linestyle=':')
    plt.legend()
    plt.title("Martha's Vineyard Polar Bears Attendence {} - {}".format(min(years), max(years)))
    plt.show()


# DEBUG: try out a few things
if __name__ == '__main__':
    data = sheets_read_data()
    add_dates(data)
    first_plot(data)

