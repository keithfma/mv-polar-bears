"""
Build static webpage exploring MV Polar Bears dataset
"""

# TODO: include cumulative plots for total attendees and total num polar bears

import os
from mvpb_util import get_client, read_sheet
from mvpb_data import get_weather_conditions, get_water_conditions
from mvpb_forecast import tomorrow as forecast_tomorrow
from mvpb_forecast import retrospective as forecast_retrospective
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
        plot_width=1700,
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

    return bk_embed.components(fig)


def cumul_bears_plot(data):
    """
    Arguments:
        data: pandas dataframe
        kind: field name to plot, only GROUP and NEWBIES make sense 

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
        plot_width=1700,
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


def get_forecast_data(data, darksky_keyfile):
    """
    Return forecast for attendence, weather, and water conditions
    """
    # init time for next day
    tomorrow = data.index[-1] + timedelta(days=1)

    # get weather for tomorrow
    with open(os.path.expanduser(darksky_keyfile), 'r') as fp:
        darksky_key = json.load(fp)['secret_key']
    weather = get_weather_conditions(darksky_key, dt=tomorrow)

    # get water for tomorrow
    water = get_water_conditions(tomorrow, None)

    # get attendance for tomorrow
    grp_mean, grp_std = forecast_tomorrow(data)

    forecast = {
        'GROUP': grp_mean,
        'GROUP_STD': grp_std,
        **weather,
        **water,
        }

    return forecast


def forecast_plot(time, obs, pred_mean, pred_std):
    """
    Plot retrospective forecast mean, variance, and residuals
    """
    try:
        upper_bound = pred_mean + pred_std
        lower_bound = pred_mean - pred_std
        pred_mean[pred_mean < 0] = 0
        upper_bound[upper_bound < 0] = 0
        lower_bound[lower_bound < 0] = 0
    except:
        set_trace()

    # create figure for forecast
    fig_a = bk_plt.figure(
        title="Retrospective Attendance Forecast",
        x_axis_label='Date',
        x_axis_type='datetime',
        y_axis_label='# Attendees',
        x_range=(min(time), max(time)),
        plot_width=1700,
        tools="pan,wheel_zoom,box_zoom,reset",
        logo=None
        )

    # generate forecast plot
    fig_a.line(time, obs,
        legend='Observed',
        line_color='mediumblue',
        line_width=2
        )
    fig_a.line(time, pred_mean,
        legend='Predicted',
        line_color='forestgreen',
        line_width=1
        )
    patch_x = np.append(time, time[::-1])
    patch_y = np.append(upper_bound, lower_bound[::-1])
    fig_a.patch(patch_x, patch_y,
        legend='Predicted, Margin of Error (1-sigma)',
        color='forestgreen',
        fill_alpha=0.5,
        line_alpha=0
        )

    # additional formatting
    set_font_size(fig_a)

    # create figure for forecast
    fig_b = bk_plt.figure(
        title="Attendance Forecast Error",
        x_axis_label='Date',
        x_axis_type='datetime',
        y_axis_label='# Attendees',
        x_range=(min(time), max(time)),
        plot_width=1700,
        tools="pan,wheel_zoom,box_zoom,reset",
        logo=None
        )
    fig_b.line(time, obs - pred_mean,
        legend='Prediction Error (Observed - Predicted)',
        line_color='red',
        line_width=2
        )

    # additional formatting
    set_font_size(fig_b)

    return bk_embed.components(bk_layouts.column(fig_a, fig_b))


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


def update(google_keyfile, darksky_keyfile, log_level):
    """
    Get data and build static HTML / JS site
    
    Arguments:
        google_keyfile: Google Sheets API key
        darksky_keyfile: DarkSky API key
        log_level: string, logging level, one of 'critical', 'error',
            'warning', 'info', 'debug'
    """
    lvl = getattr(logging, log_level.upper())
    logging.basicConfig(level=lvl)
    logger.setLevel(lvl)

    logger.info('Updating MV Polar Bears website')

    client, doc, sheet = get_client(google_keyfile)
    data = read_sheet(sheet) 
    
    cumul_script, cumul_div = cumul_bears_plot(data)
    recent_bar_script, recent_bar_div = daily_bar_plot(data, 21)
    daily_bar_script, daily_bar_div = daily_bar_plot(data)
    daily_table = get_table_data(data)
    forecast_data = get_forecast_data(data, darksky_keyfile)
    scatter_scripts, scatter_divs = all_scatter_plots(data)

    time = data.index.values
    obs = data['GROUP'].fillna(0).values
    mean, std = forecast_retrospective(data, first=1400)
    forecast_script, forecast_div = forecast_plot(time, obs, mean, std)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
        autoescape=jinja2.select_autoescape(['html', 'css'])
        )

    index_template = env.get_template('index.html')
    with open(os.path.join(PUBLISH_DIR, 'index.html'), 'w') as index_fp:
        index_content = index_template.render(
            title=WEBPAGE_TITLE,
            daily_table=daily_table,
            recent_bar_script=recent_bar_script, recent_bar_div=recent_bar_div,
            daily_bar_div=daily_bar_div, daily_bar_script=daily_bar_script,
            cumul_div=cumul_div, cumul_script=cumul_script,
            last_update=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            scatter_divs=scatter_divs, scatter_scripts=scatter_scripts,
            forecast=forecast_data,
            forecast_div=forecast_div, forecast_script=forecast_script,
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
    ap.add_argument('darksky_key', help="Path to DarkSky API key file")
    ap.add_argument('--log_level', help='Log level to display',
                    choices=['critical', 'error', 'warning', 'info', 'debug'],
                    default='info')
    args = ap.parse_args()

    # run
    update(args.google_key, args.darksky_key, args.log_level) 
