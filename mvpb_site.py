"""
Build static webpage exploring MV Polar Bears dataset
"""

# TODO: include cumulative plots for total attendees and total num polar bears

import os
from mvpb_util import get_client, read_sheet
from bokeh import plotting as bk_plt
from bokeh import models as bk_model
from bokeh import embed as bk_embed
import jinja2
import pytz
import dateutil
from numpy import nan
from pkg_resources import resource_filename
from pdb import set_trace
import argparse
import logging
from datetime import datetime

# constants
TEMPLATES_DIR = 'templates'
WEBPAGE_TITLE = 'MV Polar Bears!'
PUBLISH_DIR = 'docs'
GROUP_COLOR = 'royalblue'
NEWBIES_COLOR = 'forestgreen'
FONT_SIZE = '20pt'
DAY_TO_MSEC = 60*60*24*1000
US_EASTERN = pytz.timezone('US/Eastern')

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


def daily_bar_plot(data):
    """
    Arguments:
        data: pandas dataframe

    Returns: script, div
        script: javascript function controlling plot, wrapped in <script> HTML tags
        div: HTML <div> modified by javascript to show plot
    """
    logger.info('Generating daily bar plot')

    # create figure
    fig = bk_plt.figure(
        title="Daily Attendence",
        x_axis_label='Date',
        x_axis_type='datetime',
        y_axis_label='# Attendees',
        plot_width=1700,
        tools="pan,wheel_zoom,box_zoom,reset",
        logo=None
        )
    
    # add bar plots
    fig.vbar(
        x=data.index, width=DAY_TO_MSEC, bottom=0, top=data['GROUP'],
        color=GROUP_COLOR, legend='Group')
    fig.vbar(
        x=data.index, width=DAY_TO_MSEC, bottom=-data['NEWBIES'], top=0,
        color=NEWBIES_COLOR, legend='Newbies')

    # additional formatting
    set_font_size(fig)
    set_ylabel_to_positive(fig)

    return bk_embed.components(fig)


def weekly_bar_plot(data):
    """
    Arguments:
        data: pandas dataframe

    Returns: script, div
        script: javascript function controlling plot, wrapped in <script> HTML tags
        div: HTML <div> modified by javascript to show plot
    """
    logger.info('Generating weekly bar plot')

    # compute weekly sums
    weekly = data[['GROUP', 'NEWBIES']].resample('W').sum()

    # create figure
    fig = bk_plt.figure(
        title="Weekly Attendence",
        x_axis_label='Week Start Date',
        x_axis_type='datetime',
        y_axis_label='Total # Attendees',
        plot_width=1700,
        tools="pan,wheel_zoom,box_zoom,reset",
        logo=None
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


def get_table_data(data):
    """
    Munge data to build a daily view of all available data
    
    Arguments:
        data: pandas dataframe

    Returns:
        list of dicts, each containing data for a single day, with no gaps
    """
    logger.info('Generating summary table')

    table_data = data.replace(nan, '-')
    table_dict = table_data.T.to_dict()
    table = []
    for date in sorted(table_data.index):
        table.append(table_dict[date])
    table.sort(key=lambda x: x['DATE'], reverse=True)
    return table


def get_forecast_data():
    """
    Return forecast for attendence, weather, and water conditions
    """
    pass


def forecast_plot():
    """
    Plot retrospective forecast mean, variance, and residuals
    """
    pass


def scatter_plot(data, xname, yname):
    """
    Generate simple scatter plot for pair of variables

    Arguments:
        data: pandas dataframe
        xname, yname: strings, column names for x and y variables in plot

    Returns: script, div
        script: javascript function controlling plot, wrapped in <script> HTML tags
        div: HTML <div> modified by javascript to show plot
    """
    logger.info('Generating scatter plot, x = "{}", y = "{}"'.format(xname, yname))

    # compute padded ranges
    pad_frac = 0.025
    xpad = pad_frac*(max(data[xname]) - min(data[xname]))
    ypad = pad_frac*(max(data[yname]) - min(data[yname]))
    xrng = (min(data[xname]) - xpad, max(data[xname]) + xpad)
    yrng = (min(data[yname]) - ypad, max(data[yname]) + ypad)

    # create figure
    fig = bk_plt.figure(
        title="",
        x_axis_label=xname,
        x_range=xrng,
        y_axis_label=yname,
        y_range=yrng,
        plot_width=800,
        plot_height=600,
        match_aspect=True,
        tools="pan,wheel_zoom,box_zoom,reset",
        logo=None
        )
    
    # add scatter plot
    fig.circle(
        data[xname], data[yname],
        size=10,
        color='orangered',
        alpha=0.75,
        )

    # additional formatting
    set_font_size(fig)

    return bk_embed.components(fig)


def all_scatter_plots(data):
    """
    Generate scatter plots for all hard-coded variable pairs

    Arguments:
        data: pandas dataframe

    Returns: scripts, divs
        scripts: list of scripts, each as returned by scatter_plot() 
        divs: list of divs, each as returned by scatter_plot()
    """
    # constants
    xynames = [
        ('NEWBIES', 'GROUP'),
        ('AIR-TEMPERATURE-DEGREES-F', 'GROUP'),
        ('HUMIDITY-PERCENT', 'GROUP'),
        # ('CLOUD-COVER-PERCENT', 'GROUP'),  # data does not appear reliable
        ('PRECIP-PROBABILITY', 'GROUP'),
        ('WIND-SPEED-MPH', 'GROUP'),
        ('WAVE-HEIGHT-METERS', 'GROUP'),
        ]

    # generate all plots
    scripts = []
    divs = []
    for xyname in xynames:
        script, div = scatter_plot(data, xyname[0], xyname[1])
        scripts.append(script)
        divs.append(div)

    return scripts, divs


def update(keyfile, log_level):
    """
    Get data and build static HTML / JS site
    
    Arguments:
        keyfile: Google Sheets API key
        log_level: string, logging level, one of 'critical', 'error',
            'warning', 'info', 'debug'
    """
    lvl = getattr(logging, log_level.upper())
    logging.basicConfig(level=lvl)
    logger.setLevel(lvl)

    logger.info('Updating MV Polar Bears website')

    client, doc, sheet = get_client(keyfile)
    data = read_sheet(sheet) 
    
    daily_bar_script, daily_bar_div = daily_bar_plot(data)
    weekly_bar_script, weekly_bar_div = weekly_bar_plot(data)
    daily_table = get_table_data(data)
    scatter_scripts, scatter_divs = all_scatter_plots(data)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
        autoescape=jinja2.select_autoescape(['html', 'css'])
        )

    index_template = env.get_template('index.html')
    with open(os.path.join(PUBLISH_DIR, 'index.html'), 'w') as index_fp:
        index_content = index_template.render(
            title=WEBPAGE_TITLE,
            daily_table=daily_table,
            daily_bar_div=daily_bar_div,
            daily_bar_script=daily_bar_script,
            weekly_bar_div=weekly_bar_div,
            weekly_bar_script=weekly_bar_script,
            last_update=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            scatter_divs=scatter_divs,
            scatter_scripts=scatter_scripts
            )
        index_fp.write(index_content)

    style_template = env.get_template('style.css')
    with open(os.path.join(PUBLISH_DIR, 'style.css'), 'w') as style_fp:
        style_content = style_template.render()
        style_fp.write(style_content)

    logger.info('Update complete')


# command line interface
if __name__ == '__main__':
    
    # arguments
    ap = argparse.ArgumentParser(
        description="Update MV Polar Bears website",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('google_key', help="Path to Google API key file")
    ap.add_argument('--log_level', help='Log level to display',
                    choices=['critical', 'error', 'warning', 'info', 'debug'],
                    default='info')
    args = ap.parse_args()

    # run
    update(args.google_key, args.log_level) 
