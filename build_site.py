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
from bokeh import models as bmdl


# constants
# TODO: move to a config file
KEY_FILE = 'secret.json'
DOC_TITLE = 'MV Polar Bears Attendence'
SHEET_TITLE = 'Data'

GROUP_COLOR = 'royalblue'
NEWBIES_COLOR = 'forestgreen'
FONT_SIZE = '20pt'
DAY_TO_MSEC = 60*60*24*1000


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
    data.set_index(pd.to_datetime(data[['YEAR', 'MONTH', 'DAY']]), inplace=True)


def set_font_size(fig):
    """Update font sizes in input Bokeh figures"""
    fig.title.text_font_size = FONT_SIZE
    fig.xaxis.axis_label_text_font_size = FONT_SIZE
    fig.yaxis.axis_label_text_font_size = FONT_SIZE
    fig.xaxis.major_label_text_font_size = FONT_SIZE
    fig.yaxis.major_label_text_font_size = FONT_SIZE
    fig.legend.label_text_font_size = FONT_SIZE


def set_ylabel_to_positive(fig):
    """Replace negative-valued y labels with thier absolute value"""
    fig.yaxis.formatter = bmdl.FuncTickFormatter(code="return Math.abs(tick)")


def daily_bar_plot(data, fname):
    """
    Arguments:
        data: pandas dataframe
        fname: filename for html file
    """
    # set output file
    bplt.output_file(fname)
    
    # create figure
    min_year = min(data['YEAR'])
    max_year = max(data['YEAR'])
    fig = bplt.figure(
        title="Daily Attendence {} to {}".format(min_year, max_year),
        x_axis_label='Date',
        x_axis_type='datetime',
        y_axis_label='# Attendees',
        plot_width=1700,
        )
    
    # add bar plots
    fig.vbar(
        x=data['DATE'], width=DAY_TO_MSEC, bottom=0, top=data['GROUP'],
        color=GROUP_COLOR, legend='Group')
    fig.vbar(
        x=data['DATE'], width=DAY_TO_MSEC, bottom=-data['NEWBIES'], top=0,
        color=NEWBIES_COLOR, legend='Newbies')

    # additional formatting
    set_font_size(fig)
    set_ylabel_to_positive(fig)

    # generate file and display in browser
    bplt.show(fig)

    return fig


def weekly_bar_plot(data, fname):
    """
    Arguments:
        data: pandas dataframe
        fname: filename for html file
    """
    # compute weekly sums
    weekly = data[['GROUP', 'NEWBIES']].resample('W').sum()

    # set output file
    bplt.output_file(fname)
    
    # create figure
    min_year = min(data['YEAR'])
    max_year = max(data['YEAR'])
    fig = bplt.figure(
        title="Weekly Attendence {} to {}".format(min_year, max_year),
        x_axis_label='Week Start Date',
        x_axis_type='datetime',
        y_axis_label='Total # Attendees',
        plot_width=1700,
        )
    
    # add bar plots
    fig.vbar(
        x=weekly.index, width=DAY_TO_MSEC*7, bottom=0, top=weekly['GROUP'],
        color=GROUP_COLOR, legend='Group')
    fig.vbar(
        x=weekly.index, width=DAY_TO_MSEC*7, bottom=-weekly['NEWBIES'], top=0,
        color=NEWBIES_COLOR, legend='Newbies')

    # additional formatting
    set_font_size(fig)
    set_ylabel_to_positive(fig)

    # generate file and display in browser
    bplt.show(fig)

    return fig


# DEBUG: try out a few things
if __name__ == '__main__':
    # data = sheets_read_data()
    # add_dates(data)
    # fig = daily_bar_plot(data, 'delete_me.html')
    fig = weekly_bar_plot(data, 'delete_me.html')

