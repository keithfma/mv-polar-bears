"""
Scratch space for developing key functions before it is clear where they will
live in the final package
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from numpy import nan
from bokeh import plotting as bk_plt
from bokeh import models as bk_model
from bokeh import embed as bk_embed
import jinja2
import os


# config constants
KEY_FILE = 'secret.json'
DOC_TITLE = 'MV Polar Bears Attendence'
SHEET_TITLE = 'Data'

# plot format constants
GROUP_COLOR = 'royalblue'
NEWBIES_COLOR = 'forestgreen'
FONT_SIZE = '20pt'
DAY_TO_MSEC = 60*60*24*1000

# webpage constants
WEBPAGE_TITLE = 'MV Polar Bears!'
PUBLISH_DIR = 'docs'


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
    fig.yaxis.formatter = bk_model.FuncTickFormatter(code="return Math.abs(tick)")


def daily_bar_plot(data, fname):
    """
    Arguments:
        data: pandas dataframe
        fname: filename for html file
    """
    # set output file
    bk_plt.output_file(fname)
    
    # create figure
    min_year = min(data['YEAR'])
    max_year = max(data['YEAR'])
    fig = bk_plt.figure(
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
    bk_plt.show(fig)

    return fig


def weekly_bar_plot(data):
    """
    Arguments:
        data: pandas dataframe

    Returns: script, div
        script:
        div:
    """
    # compute weekly sums
    weekly = data[['GROUP', 'NEWBIES']].resample('W').sum()

    # create figure
    min_year = min(data['YEAR'])
    max_year = max(data['YEAR'])
    fig = bk_plt.figure(
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

    return bk_embed.components(fig)


# TODO: write command-line tool to build site
if __name__ == '__main__':
    # data = sheets_read_data()
    # add_dates(data)
    # fig = daily_bar_plot(data, 'delete_me.html')
    script, div = weekly_bar_plot(data)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('templates'),
        autoescape=jinja2.select_autoescape(['html'])
        )

    index_template = env.get_template('index.html')
    with open(os.path.join(PUBLISH_DIR, 'index.html'), 'w') as index_fp:
        index_content = index_template.render(
            title=WEBPAGE_TITLE
            )
        index_fp.write(index_content)



