"""
Generate static website for simple data visualization
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
import requests
import pytz
from datetime import datetime, timedelta
import json
import math


# config constants
GOOGLE_KEY_FILE = 'google_secret.json'
GOOGLE_DOC_TITLE = 'MV Polar Bears'
GOOGLE_SHEET_ATTEND_TITLE = 'Attendance'
GOOGLE_SHEET_WEATHER_TITLE = 'Weather'
DARKSKY_KEY_FILE = 'darksky_secret.json'

# physical constants
INKWELL_LAT = 41.452463 # degrees N
INKWELL_LON = -70.553526 # degrees E
US_EASTERN = pytz.timezone('US/Eastern')

# plot format constants
GROUP_COLOR = 'royalblue'
NEWBIES_COLOR = 'forestgreen'
FONT_SIZE = '20pt'
DAY_TO_MSEC = 60*60*24*1000

# webpage constants
WEBPAGE_TITLE = 'MV Polar Bears!'
PUBLISH_DIR = 'docs'

# misc constants


def get_weather_conditions(key_file, lon, lat, dt):
    """
    Retrieve forecast or observed weather conditions
    
    Note: using the forecast.io Dark Sky API, documented here:
        https://darksky.net/dev/docs
    
    Arguments:
        lon: longitude of a location (in decimal degrees). Positive is east,
            negative is west
        lat: latitude of a location (in decimal degrees). Positive is north,
            negative is south.
        dt: datetime, timezone-aware, time for observation
    
    Returns: Dict with the following fields (renamed from forecast.io):
        cloudCover: The percentage of sky occluded by clouds, between 0 and 1, inclusive.
        humidity: The relative humidity, between 0 and 1, inclusive.
        precipIntensity: The intensity (in inches of liquid water per hour) of precipitation occurring at the given time. This value is conditional on probability (that is, assuming any precipitation occurs at all) for minutely data points, and unconditional otherwise.
        precipProbability: The probability of precipitation occurring, between 0 and 1, inclusive.
        summary: A human-readable text summary of this data point.
        temperature: The air temperature in degrees Fahrenheit.
        windBearing: The direction that the wind is coming from in degrees, with true north at 0° and progressing clockwise. (If windSpeed is zero, then this value will not be defined.)
        windGust: The wind gust speed in miles per hour.
        windSpeed: The wind speed in miles per hour.
        ...
    """
    # request data from Dark Sky API (e.g. forecast.io)
    with open(key_file, 'r') as fp:
        key = json.load(fp)['secret_key']
    stamp = math.floor(dt.timestamp())
    url = 'https://api.darksky.net/forecast/{}/{:.10f},{:.10f},{}'.format(
        key, lat, lon, stamp)
    params = {'units': 'us'}
    resp = requests.get(url, params)
    resp.raise_for_status()
    data = resp.json()
    
    # reformat resulting data
    fields = {  # forecast.io names -> local names
        'cloudCover': 'CLOUD-COVER-PERCENT',
        'humidity': 'HUMIDITY-PERCENT',
        'precipIntensity': 'PRECIP-RATE-INCHES-PER-HR',
        'precipProbability': 'PRECIP-PROBABILITY',
        'summary': 'SUMMARY',
        'temperature': 'AIR-TEMPERATURE-DEGREES-F',
        'windBearing': 'WIND-BEARING-CW-DEGREES-FROM-N',
        'windGust': 'WIND-GUST-SPEED-MPH',
        'windSpeed': 'WIND-SPEED-MPH',
        }
    return {v: data['currently'].get(n, None) for n, v in fields.items()}
    
def get_water_conditions():
    """
    Retrieve observed water conditions
    
    Arguments:
        ?
    
    Returns:
        ?
    """
    pass


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
    client = sheets_get_client(GOOGLE_KEY_FILE)
    doc = client.open(GOOGLE_DOC_TITLE)
    sheet = doc.worksheet(GOOGLE_SHEET_ATTEND_TITLE)
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


def daily_bar_plot(data):
    """
    Arguments:
        data: pandas dataframe

    Returns: script, div
        script: javascript function controlling plot, wrapped in <script> HTML tags
        div: HTML <div> modified by javascript to show plot
    """
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
        x=data['DATE'], width=DAY_TO_MSEC, bottom=0, top=data['GROUP'],
        color=GROUP_COLOR, legend='Group')
    fig.vbar(
        x=data['DATE'], width=DAY_TO_MSEC, bottom=-data['NEWBIES'], top=0,
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


def resample_to_daily(data):
    """Resample input dataframe to daily resolution (initial cleaning step)"""
    lookup_day = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    data = data.resample('D').mean() # daily frequency, no gaps
    data['DATE'] = pd.Series(
        {x: x.to_pydatetime().date() for x in data.index})
    data['YEAR'] = data['DATE'].apply(lambda x: x.year)
    data['MONTH'] = data['DATE'].apply(lambda x: x.month)
    data['DAY'] = data['DATE'].apply(lambda x: x.day)
    data['DAY-OF-WEEK'] = data['DATE'].apply(lambda x: lookup_day[x.weekday()])
    data.set_index('DATE', drop=False, inplace=True)
    return data


def get_table_data(data):
    """
    Munge data to build a daily view of all available data
    
    Arguments:
        data: pandas dataframe

    Returns:
        list of dicts, each containing data for a single day, with no gaps
    """
    table_data = data.replace(nan, '-')
    table_dict = table_data.T.to_dict()
    table = []
    for date in sorted(table_data['DATE']):
        table.append(table_dict[date])
    table.sort(key=lambda x: x['DATE'], reverse=True)
    return table


def build_site():
    """Get/update data and build static HTML / JS site"""

    data = sheets_read_data()
    add_dates(data)
    data = resample_to_daily(data)
    
    daily_bar_script, daily_bar_div = daily_bar_plot(data)
    weekly_bar_script, weekly_bar_div = weekly_bar_plot(data)
    daily_table = get_table_data(data)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('templates'),
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
            weekly_bar_script=weekly_bar_script
            )
        index_fp.write(index_content)

    style_template = env.get_template('style.css')
    with open(os.path.join(PUBLISH_DIR, 'style.css'), 'w') as style_fp:
        style_content = style_template.render()
        style_fp.write(style_content)


# TODO: write command-line wrapper for build_site


# DEBUG / TESTING
if __name__ == '__main__':

    current_time = datetime.now(US_EASTERN) - timedelta(days=50)
    
    data = get_weather_conditions(
        DARKSKY_KEY_FILE, INKWELL_LON, INKWELL_LAT, current_time)
