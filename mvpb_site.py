"""
Build website for MV Polar Bears facebook app 
"""

import os
from mvpb_util import get_client, read_sheet
from mvpb_data import get_weather_conditions, get_water_conditions
from bokeh import plotting as bk_plt
from bokeh import models as bk_model
from bokeh import embed as bk_embed
from bokeh import layouts as bk_layouts
import jinja2
import pytz
import dateutil
from numpy import nan
from pkg_resources import resource_filename
from pdb import set_trace
import argparse
import logging
from datetime import datetime, timedelta
import json
import numpy as np
import pandas as pd

# constants
TEMPLATES_DIR = 'templates'
WEBPAGE_TITLE = 'MV Polar Bears!'
PUBLISH_DIR = 'docs'
GROUP_COLOR = 'royalblue'
NEWBIES_COLOR = 'forestgreen'
FONT_SIZE = '12pt'
DAY_TO_MSEC = 60*60*24*1000
US_EASTERN = pytz.timezone('US/Eastern')
PLOT_WIDTH = 750
PLOT_HEIGHT = 600

# init logging
logger = logging.getLogger('mv-polar-bears')


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


def format_legend(fig):
    """Simple legend formatting"""
    fig.legend.location = "top_left"


def daily_bar_plot(data, limit=None):
    """
    Arguments:
        data: pandas dataframe
        limit: int, max number of results to include, set None to include all

    Returns: script, div
        script: javascript function controlling plot, wrapped in <script> HTML tags
        div: HTML <div> modified by javascript to show plot
    """
    logger.info('Generating daily bar plot')

    # truncate data, if requested
    if not limit:
        limit = 0
    time = data.index[-limit:]
    grp = data['GROUP'][-limit:]
    newb = data['NEWBIES'][-limit:]

    # create figure
    fig = bk_plt.figure(
        title="Daily Attendence",
        x_axis_label='Date',
        x_axis_type='datetime',
        y_axis_label='# Attendees',
        plot_width=PLOT_WIDTH,
        plot_height=PLOT_HEIGHT,
        tools="pan,wheel_zoom,box_zoom,reset",
        logo=None
        )
    
    # add bar plots
    fig.vbar(
        x=time, width=DAY_TO_MSEC, bottom=0, top=grp,
        color=GROUP_COLOR, legend='Group')
    fig.vbar(
        x=time, width=DAY_TO_MSEC, bottom=-newb, top=0,
        color=NEWBIES_COLOR, legend='Newbies')

    # additional formatting
    set_font_size(fig)
    set_ylabel_to_positive(fig)
    format_legend(fig)

    return bk_embed.components(fig)


def cumul_bears_plot(data):
    """
    Arguments:
        data: pandas dataframe

    Returns: script, div
        script: javascript function controlling plot, wrapped in <script> HTML tags
        div: HTML <div> modified by javascript to show plot
    """
    logger.info('Generating cumulative bears plot')

    # create figure
    fig = bk_plt.figure(
        title='Cumulative Number of Polar Bears',
        x_axis_label='Date',
        x_axis_type='datetime',
        y_axis_label='# Polar Bears',
        plot_width=PLOT_WIDTH,
        plot_height=PLOT_HEIGHT,
        tools="pan,wheel_zoom,box_zoom,reset",
        logo=None
        )

    # prep data
    time = data.index.values
    grp = data['GROUP'].fillna(0).cumsum()
    newb = data['NEWBIES'].fillna(0).cumsum()
    
    # plot bars
    fig.vbar(
        x=time, width=DAY_TO_MSEC, bottom=0, top=grp,
        color=GROUP_COLOR, legend='Group')
    fig.vbar(
        x=time, width=DAY_TO_MSEC, bottom=-newb, top=0,
        color=NEWBIES_COLOR, legend='Newbies')

    # additional formatting
    set_font_size(fig)
    set_ylabel_to_positive(fig)
    format_legend(fig)

    return bk_embed.components(fig)


def get_table_data(data):
    """
    Munge data to build a daily view of all available data
    
    Arguments:
        data: pandas dataframe

    Returns:
        list of dicts, each containing data for a single day, with no gaps
    """
    logger.info('Generating summary table')

    table_dict = data.T.to_dict()
    table = []
    for date in sorted(data.index):
        table.append(table_dict[date])
    table.sort(key=lambda x: x['DATE'], reverse=True)
    for ii in range(len(table)):
        for k, v in table[ii].items():
            if pd.isnull(v):
                table[ii][k] = None
    return table


def update(google_keyfile, log_level):
    """
    Get data and build static HTML / JS site
    
    Arguments:
        google_keyfile: Google Sheets API key
        log_level: string, logging level, one of 'critical', 'error',
            'warning', 'info', 'debug'
    """
    lvl = getattr(logging, log_level.upper())
    logging.basicConfig(level=lvl)
    logger.setLevel(lvl)

    logger.info('Updating MV Polar Bears website')

    client, doc, sheet = get_client(google_keyfile)
    data = read_sheet(sheet) 
    
    daily_table = get_table_data(data)
    daily_bar_script, daily_bar_div = daily_bar_plot(data)
    cumul_script, cumul_div = cumul_bears_plot(data)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
        )

    # # DEBUG
    # set_trace()
    # # /DEBUG

    site_template = env.get_template('index.html')
    with open(os.path.join(PUBLISH_DIR, 'index.html'), 'w') as site_fp:
        site_content = site_template.render(
            title=WEBPAGE_TITLE,
            daily_table=daily_table,
            daily_bar_div=daily_bar_div, daily_bar_script=daily_bar_script,
            cumul_div=cumul_div, cumul_script=cumul_script,
            last_update=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            )
        site_fp.write(site_content)

    logger.info('Update complete')


# command line interface
if __name__ == '__main__':
    
    # arguments
    ap = argparse.ArgumentParser(
        description="Generate MV Polar Bears blog post",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('google_key', help="Path to Google API key file")
    ap.add_argument('--log_level', help='Log level to display',
                    choices=['critical', 'error', 'warning', 'info', 'debug'],
                    default='info')
    args = ap.parse_args()

    # run
    update(args.google_key, args.log_level) 
