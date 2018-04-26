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
import dateutil
from pdb import set_trace
import logging
from time import sleep


# config constants
GOOGLE_KEY = 'google_secret.json'
DOC_TITLE = 'MV Polar Bears'
SHEET_TITLE = 'Debug'
DARKSKY_KEY = 'darksky_secret.json'
NDBC_STATION = '44020' # Buoy in Nantucket Sound
LOG_LEVEL = logging.INFO
GOOGLE_WAIT_SEC = 60

# physical constants
INKWELL_LAT = 41.452463 # degrees N
INKWELL_LON = -70.553526 # degrees E
US_EASTERN = pytz.timezone('US/Eastern')

# plot format constants
GROUP_COLOR = 'royalblue'
NEWBIES_COLOR = 'forestgreen'
FONT_SIZE = '20pt'
DAY_TO_MSEC = 60*60*24*1000

# status codes
SUCCESS = 0            # completed successfully, hooray!
GOOGLE_QUOTA_ERROR = 1 #  Google API read / write quota exceeded

# webpage constants
WEBPAGE_TITLE = 'MV Polar Bears!'
PUBLISH_DIR = 'docs'

# init logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger('mv-polar-bears')
logger.setLevel(LOG_LEVEL)


def get_client(key_file=GOOGLE_KEY, doc_title=DOC_TITLE, sheet_title=SHEET_TITLE):
    """
    Return interfaces to Google Sheets data store
    
    Arguments:
        key_file: Google Sheets / Drive API secret key file
        doc_title: Title / filename for google spreadsheet
        sheet_title: Title for worksheet within google spreadsheet
    
    Returns:
        client: gspread.client.Client
        doc: gspread.models.Spreadsheet
        sheet: gspread.models.Worksheet
    """
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(key_file, scope)
    client = gspread.authorize(creds)
    doc = client.open(doc_title)
    sheet = doc.worksheet(sheet_title)
    return client, doc, sheet


def read_sheet(sheet):
    """
    Read current data from Google Sheets

    Arguments:
        sheet: gspread sheet, connected

    Return: pd dataframe containing current data
    """
    content = sheet.get_all_records(default_blank=nan)
    content = pd.DataFrame(content)
    logger.info('Read sheet contents')
    return content


def get_column_indices(sheet, base=0):
    """
    Return lookup table {column name: column index}
    
    Arguments:
        sheet: gspread sheet, connected
        base: 0 or 1, index of first column
    
    Return: lookup table
    """
    hdr = sheet.row_values(1)
    return {name: ii+base for ii, name in enumerate(hdr)}


def _parse_datetime(date_str, time_str):
    """Utility for parsing DATE and TIME columns to python datetime"""
    dt = dateutil.parser.parse(date_str + ' ' + time_str) 
    dt = dt.replace(tzinfo=US_EASTERN)
    return dt    


def add_missing_days(sheet):
    """
    Add (empty) rows in sheet for missing days
    
    Arguments:
        sheet: gspread sheet, connected

    Return: exit status code, possible values are SUCCESS, GOOGLE_QUOTA_ERROR
    """

    # get current content
    content = read_sheet(sheet)
    col2ind = get_column_indices(sheet, base=0)

    # ensure minimum daily frequency by adding empty rows as needed
    rid = 3 # 1-based index to google sheet row
    prev_dt = _parse_datetime(content.iloc[1]['DATE'], content.iloc[1]['TIME'])
    for ii in range(1, len(content)): # index to local copy
        row = content.iloc[ii]
        # TODO: handle case where first col is empty (happens after API errors sometimes) 
        curr_dt = _parse_datetime(content.iloc[ii]['DATE'], content.iloc[ii]['TIME'])
        missing_days = (curr_dt - prev_dt).days - 1
        for jj in range(missing_days):
            day = prev_dt + timedelta(days=jj + 1)
            row_values = [None] * len(content.columns)
            row_values[col2ind['DATE']] = day.strftime('%Y-%m-%d')
            row_values[col2ind['TIME']] = day.strftime('%H:%M %p')
            sheet.insert_row(row_values, rid, 'USER_ENTERED')
            logger.info('Added row for {} at index {}'.format(day, rid))
            rid += 1
        prev_dt = curr_dt
        rid += 1

    return SUCCESS


def add_missing_data():
    
    # connect and get current content
    client, doc, sheet = get_client()
    content = read_sheet()
    
    # compile list of cells to update at-once
    to_update = []
    for ii in range(len(content)):
        row = content.iloc[ii]
        rid = ii + 2
        
        # update day-of-week?
        if pd.isnull(row['DAY-OF-WEEK']):
            dt = datetime.strptime(row['DATE'], '%Y-%m-%d')
            dow = dt.strftime('%A')
            cell = gspread.models.Cell(rid, cid['DAY-OF-WEEK'], dow)
            to_update.append(cell)
        
        # update weather?
        if pd.isnull(row['AIR-TEMPERATURE-DEGREES-F']):
            # get time
            dt = dateutil.parser.parse(row['DATE'] + ' ' + row['TIME']) 
            dt = dt.replace(tzinfo=US_EASTERN)
            # fetch weather at time
            
        
    # update all at once
    if to_update:
        sheet.update_cells(to_update, 'USER_ENTERED')

    return to_update


def get_weather_conditions(lon, lat, dt, key_file=DARKSKY_KEY):
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
        key_file: JSON file containing Dark Sky API key
    
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

    
# def _populate_date_time():
#     """Populate the date and time columns in the Google sheet - used once"""
#     client, doc, sheet = get_client()
#         
#     # gather date parts from sheet
#     year_col = sheet.find('YEAR').col
#     years = sheet.col_values(year_col, 'UNFORMATTED_VALUE')
#     month_col = sheet.find('MONTH').col
#     months = sheet.col_values(month_col, 'UNFORMATTED_VALUE')
#     day_col = sheet.find('DAY').col
#     days = sheet.col_values(day_col, 'UNFORMATTED_VALUE')        
# 
#     # convert to formatted date and time
#     dates = ['DATE']
#     times = ['TIME']
#     for yy, mm, dd in zip(years[1:], months[1:], days[1:]):
#         dt = datetime(yy, mm, dd, 7, 30, tzinfo=US_EASTERN)
#         dates.append(dt.strftime('%Y-%m-%d'))
#         times.append(dt.strftime('%H:%M %p'))
#     
#     # update sheet
#     sheet.add_cols(2)
#     date_col = sheet.col_count + 1
#     time_col = sheet.col_count + 2
#     
#     date_cells = sheet.range(1, date_col, len(dates), date_col)
#     for date, date_cell in zip(dates, date_cells):
#         date_cell.value = date
#     sheet.update_cells(date_cells, 'USER_ENTERED')
#     
#     time_cells = sheet.range(1, time_col, len(times), time_col)
#     for time, time_cell in zip(times, time_cells):
#         time_cell.value = time
#     sheet.update_cells(time_cells, 'USER_ENTERED')
#     
#   return date_cells, time_cells



    
def get_water_conditions():
    """
    Retrieve observed water conditions at specified time
    
    Loads data from local pickle file, if available, else downloads from NOAA
    parses to a dataframe, and pickles it.
    
    Data come from the nearest NOAA station as historical and realtime (last
    45 days) datasets, formatted as tabular text files, see:
        http://www.ndbc.noaa.gov/station_page.php?station=44020
    
    Arguments:
        dt: datetime, timezone aware, observation time
    
    Returns: dict with the following fields:
        ...
    """
    if os.path.isfile(N_PICKLE):
        raise NotImplementedError
    
    # download historical data
    
# http://www.nws.noaa.gov/om/marine/internet.htm
#  http://tgftp.nws.noaa.gov/data/forecasts/marine/coastal/an/anz233.txt    
    
# resp = requests.get('http://marine.weather.gov/MapClick.php?lat=41.4378&lon=-70.771&FcstType=digitalDWML')


# http://www.ndbc.noaa.gov/rt_data_access.shtml
# 'http://www.ndbc.noaa.gov/data/realtime2/BZBM3.txt'    

# http://www.ndbc.noaa.gov/station_page.php?station=BZBM3
# http://www.ndbc.noaa.gov/station_realtime.php?station=BZBM3
# http://www.ndbc.noaa.gov/data/realtime2/BZBM3.txt
# http://www.ndbc.noaa.gov/measdes.shtml#stdmet
# http://www.ndbc.noaa.gov/station_history.php?station=bzbm3
# http://www.ndbc.noaa.gov/data/historical/stdmet/bzbm3h2017.txt.gz


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
# TODO: write function for update_data
# TODO: write command-line wrapper for update_data


def _is_google_quota_error(err):
    """Return True if input 'err' is a Google quota error, else False"""
    tf = False
    if isinstance(err, gspread.exceptions.APIError):
        msg = err.response.json()['error']
        code = msg['code']
        status = msg['status']
        if  code == 429 and status == 'RESOURCE_EXHAUSTED':
            tf = True
    return tf


def retry_until_success(func, *args):
    """
    Run function until it completes successfully, handling API rate errors

    Arguments:
        func: callable, function to be run
        *args: arbitrary arguments to func
    """
    while True:
        try: 
            # attempt to run function
            func(*args)
        except Exception as err:
            if _is_google_quota_error(err):
                # handle rate error, retry after delay
                msg = 'Google quota exhausted, waiting {}s'.format(GOOGLE_WAIT_SEC)
                logger.warning(msg)
                sleep(GOOGLE_WAIT_SEC)
                continue
            else:
                # some other error, fail
                raise err
        # completed without error
        break 


# DEBUG / TESTING
if __name__ == '__main__':

    # working on an "update data" function
    client, doc, sheet = get_client() 
    
    retry_until_success(add_missing_days, sheet)

    # current_time = datetime.now(US_EASTERN) - timedelta(days=50)
    
    # data = get_weather_conditions(
    #     DARKSKY_KEY_FILE, INKWELL_LON, INKWELL_LAT, current_time)
