"""
Scratch space for developing key functions before it is clear where they will
live in the final package
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from numpy import nan
from matplotlib import pyplot as plt
from bokeh import plotting as bplt

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


def first_plot(data, fname):
    """Display attendence vs time plot"""


    # set output file
    bplt.output_file(fname)

    # create figure
    min_year = min(data['YEAR'])
    max_year = max(data['YEAR'])
    fig = bplt.figure(
        title="Martha's Vineyard Polar Bears Attendence {} - {}".format(min_year, max_year),
        x_axis_label='Date',
        y_axis_label='Number Attendees'
        )

    # add lines
    fig.line(data['DATE'], data['GROUP'], legend='Group', line_color='blue')
    fig.line(data['DATE'], data['NEWBIES'], legend='Newbies', line_color='green')

    # generate file and display in browser
    bplt.show(fig)
    

# DEBUG: try out a few things
if __name__ == '__main__':
    data = sheets_read_data()
    add_dates(data)
    first_plot(data, 'delete_me.html')

