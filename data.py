"""
Generate static website for simple data visualization
"""

import gspread
import pandas as pd
from numpy import nan
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
import io
import re
import pickle
import numpy as np
import argparse
from pkg_resources import resource_filename
from mv_polar_bears.util import get_client, read_sheet

# constants
BUOY_NUM = '44020' # Buoy in Nantucket Sound
DATA_DIR = 'data'
# TODO: don't bother with the pickle file
BUOY_HISTORICAL = os.path.join(DATA_DIR, 'historical.pkl')
LOG_LEVEL = logging.INFO
GOOGLE_WAIT_SEC = 60
INKWELL_LAT = 41.452463 # degrees N
INKWELL_LON = -70.553526 # degrees E
US_EASTERN = pytz.timezone('US/Eastern')
UTC = pytz.timezone('UTC')

# init logging
logger = logging.getLogger('mv-polar-bears')


# TODO: use DATETIME column that is now returned by read_sheet


def is_google_quota_error(err):
    """Return True if input 'err' is a Google quota error, else False"""
    tf = False
    if isinstance(err, gspread.exceptions.APIError):
        msg = err.response.json()['error']
        code = msg['code']
        status = msg['status']
        if  code == 429 and status == 'RESOURCE_EXHAUSTED':
            tf = True
    return tf


def is_darksky_quota_error(err):
    """Return Tre if input 'err' is a DarkSky quota error, else False"""
    tf = False
    if isinstance(err, requests.exceptions.HTTPError):
        resp = err.response
        if resp.status_code == 403 and 'darksky' in resp.url:
            tf = True
    return tf


def api(func):
    """
    Wrap input function to handle known API issues (e.g., rate limits, errors)

    Arguments:
        func: callable, to be wrapped and returned

    Returns: callable, wrapped version of func that handles API issues
    """

    def wrapper(*args, **kwargs):
        while True:
            # retry until some condition breaks the loop
            
            try: 
                # attempt to run function
                func(*args, **kwargs)
            
            except Exception as err:
                # handle known exceptions

                if is_google_quota_error(err):
                    # handle google rate error, retry after delay
                    msg = 'Google quota exhausted, waiting {}s'.format(GOOGLE_WAIT_SEC)
                    logger.warning(msg)
                    sleep(GOOGLE_WAIT_SEC)
                    continue

                if is_darksky_quota_error(err):
                    # DarkSky API quota exceeded, log error and exit
                    msg = 'DarkSky API quota exceeded, terminating function'
                    logger.error(msg)
                    break
                
                else:
                    # some other error, fail
                    raise err
            
            # completed without error
            break
        
    return wrapper


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


@api
def add_missing_days(sheet):
    """
    Add (empty) rows in sheet for missing days
    
    Arguments:
        sheet: gspread sheet, connected
    """
    logger.info('Adding rows for missing days')

    # get current content
    content = read_sheet(sheet)
    col2ind = get_column_indices(sheet, base=0)

    def new_row(dt):
        """Return list of cells for a new row at datetime 'dt'"""
        row = [None] * len(content.columns)
        row[col2ind['DATE']] = dt.strftime('%Y-%m-%d')
        row[col2ind['TIME']] = dt.strftime('%H:%M %p')
        return row

    # ensure minimum daily frequency by adding empty rows as needed
    rid = 3 # 1-based index to google sheet row
    prev_dt = parse_datetime(content.iloc[1]['DATE'], content.iloc[1]['TIME'])
    for ii in range(1, len(content)): # index to local copy
        row = content.iloc[ii]

        # delete empty rows, they are sometime created by API errors
        if all(pd.isnull(row)):
            sheet.delete_row(rid)
            logger.warning('Deleted empty row, index {}'.format(rid))
            continue

        # check for gap and fill it
        curr_dt = parse_datetime(row['DATE'], row['TIME'])
        missing_days = (curr_dt - prev_dt).days - 1
        for jj in range(missing_days):
            day = prev_dt + timedelta(days=jj + 1)
            sheet.insert_row(new_row(day), rid, 'USER_ENTERED')
            logger.info('Added row for {} at index {}'.format(day, rid))
            rid += 1
        
        # proceed to next row
        prev_dt = curr_dt
        rid += 1

    # add rows up to current day if needed
    latest = curr_dt
    today = datetime.now(tz=US_EASTERN).replace(hour=7, minute=30, second=0, microsecond=0)
    while curr_dt < today:
        curr_dt += timedelta(days=1)
        sheet.append_row(new_row(curr_dt), 'USER_ENTERED')
        logger.info('Appended row for {}'.format(curr_dt))


@api
def add_missing_dows(sheet):
    """
    Populate missing day-of-week cells

    Arguments:
        sheet: gspread sheet, connected
    """
    logger.info('Adding missing day-of-week data')

    # get current content
    content = read_sheet(sheet)

    # find col to update
    sheet_col_idx = get_column_indices(sheet, base=1)['DAY-OF-WEEK']

    # compile list of cells to update at-once
    to_update = []
    for ii in range(len(content)):
        row = content.iloc[ii]
        if pd.isnull(row['DAY-OF-WEEK']):
            dt = parse_datetime(row['DATE'], row['TIME'])
            dow = dt.strftime('%A')
            sheet_row_idx = ii + 2 # index in sheet, 1-based with header
            cell = gspread.models.Cell(sheet_row_idx, sheet_col_idx, dow)
            to_update.append(cell)
            logger.info('Queue add day-of-week {} -> {}'.format(dt, dow))

    # update all at once
    if to_update:
        sheet.update_cells(to_update, 'USER_ENTERED')
        logger.info('Updated day-of-week for {} rows'.format(len(to_update)))


@api
def add_missing_weather(sheet, darksky_key):
    """
    Populate missing weather cells

    Arguments:
        sheet: gspread sheet, connected
        darksky_key: path to DarkSky API key file
    """
    logger.info('Adding missing weather conditions data')

    # constants
    batch_size = 25 
    weather_col_names = [
        'CLOUD-COVER-PERCENT', 'HUMIDITY-PERCENT', 'PRECIP-RATE-INCHES-PER-HOUR',
        'PRECIP-PROBABILITY', 'WEATHER-SUMMARY', 'AIR-TEMPERATURE-DEGREES-F',
        'WIND-BEARING-CW-DEGREES-FROM-N', 'WIND-GUST-SPEED-MPH',
        'WIND-SPEED-MPH']     
    col_idxs = get_column_indices(sheet, base=1)
    with open(darksky_key, 'r') as fp:
        key = json.load(fp)['secret_key']

    # get current content
    content = read_sheet(sheet)

    # compile list of cells to update at-once
    to_update = []
    for ii in range(len(content)):
        row = content.iloc[ii]
        if all(pd.isnull(row[weather_col_names])):
            # get weather
            dt = parse_datetime(row['DATE'], row['TIME'])
            weather_data = get_weather_conditions(key, dt=dt)
            # queue update for all missing cells
            sheet_row_idx = ii + 2 # index in sheet, 1-based with header
            for col_name in weather_col_names:
                sheet_col_idx = col_idxs[col_name]
                new_value = weather_data[col_name]
                cell = gspread.models.Cell(sheet_row_idx, sheet_col_idx, new_value)
                to_update.append(cell)
                logger.info('Queue {} -> {} for row {}'.format(col_name, new_value, sheet_row_idx))

        # update batch
        batch_full = len(to_update) >= batch_size 
        last_batch = (ii == len(content)-1) and to_update
        if batch_full or last_batch:
            sheet.update_cells(to_update, 'USER_ENTERED')
            logger.info('Updated weather conditions data in {} cells'.format(len(to_update)))
            to_update = []


@api
def add_missing_water(sheet):
    """
    Populate missing water conditions cells

    Arguments:
        sheet: gspread sheet, connected

    """
    logger.info('Adding missing water conditions data')

    # constants
    batch_size = 25 
    water_col_names = [
        'WAVE-HEIGHT-METERS',
        'DOMINANT-WAVE-PERIOD-SECONDS',
        'AVERAGE-WAVE-PERIOD-SECONDS',
        'DOMINANT-WAVE-DIRECTION-DEGREES-CW-FROM-N',
        'WATER-TEMPERATURE-DEGREES-C']
        
    col_idxs = get_column_indices(sheet, base=1)

    # get current content
    content = read_sheet(sheet)

    # compile list of cells to update at-once
    historical = get_historical_water_conditions()
    to_update = []
    for ii in range(len(content)):
        row = content.iloc[ii]
        if all(pd.isnull(row[water_col_names])):
            # get water conditions 
            dt = parse_datetime(row['DATE'], row['TIME'])
            water_data = get_water_conditions(dt, historical)
            if any([isinstance(x, str) and x.find('MM') != -1 for x in water_data.values()]):
                set_trace()
            # queue update for all missing cells
            sheet_row_idx = ii + 2 # index in sheet, 1-based with header
            for col_name in water_col_names:
                sheet_col_idx = col_idxs[col_name]
                new_value = water_data[col_name]
                cell = gspread.models.Cell(sheet_row_idx, sheet_col_idx, new_value)
                to_update.append(cell)
                logger.info('Queue {} -> {} for row {}'.format(col_name, new_value, sheet_row_idx))

        # update batch
        batch_full = len(to_update) >= batch_size 
        last_batch = (ii == len(content)-1) and to_update
        if batch_full or last_batch:
            sheet.update_cells(to_update, 'USER_ENTERED')
            logger.info('Updated water conditions data in {} cells'.format(len(to_update)))
            to_update = []


def get_weather_conditions(key, lon=INKWELL_LON, lat=INKWELL_LAT, dt=None):
    """
    Retrieve forecast or observed weather conditions
    
    Note: using the forecast.io Dark Sky API, documented here:
        https://darksky.net/dev/docs
    
    Arguments:
        key: string, Dark Sky API key
        lon: longitude of a location (in decimal degrees). Positive is east,
            negative is west, default is Inkwell beach, Oak Bluffs
        lat: latitude of a location (in decimal degrees). Positive is north,
            negative is south, default is Inkwell beach, Oak Bluffs
        dt: datetime, timezone-aware, time for observation, default is now in
            US/Eastern timezone
    
    Returns: Dict with the following fields (renamed from forecast.io):
        CLOUD-COVER-PERCENT: The percentage of sky occluded by clouds, between
            0 and 1, inclusive.
        HUMIDITY-PERCENT: The relative humidity, between 0 and 1, inclusive.
        PRECIP-RATE-INCHES-PER-HOUR: The intensity (in inches of liquid water per
            hour) of precipitation occurring at the given time. This value is
            conditional on probability (that is, assuming any precipitation
            occurs at all) for minutely data points, and unconditional
            otherwise.
        PRECIP-PROBABILITY: The probability of precipitation occurring, between
            0 and 1, inclusive.
        WEATHER-SUMMARY: A human-readable text summary of this data point.
        AIR-TEMPERATURE-DEGREES-F: The air temperature in degrees Fahrenheit.
        WIND-BEARING-CW-DEGREES-FROM-N: The direction that the wind is coming
            from in degrees, with true north at 0° and progressing clockwise.
            (If windSpeed is zero, then this value will not be defined.)
        WIND-GUST-SPEED-MPH: The wind gust speed in miles per hour.
        WIND-SPEED-MPH: The wind speed in miles per hour.
    """
    # set defaults
    if not dt:
        dt = datetime.now(tz=US_EASTERN)

    # request data from Dark Sky API (e.g. forecast.io)
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
        'precipIntensity': 'PRECIP-RATE-INCHES-PER-HOUR',
        'precipProbability': 'PRECIP-PROBABILITY',
        'summary': 'WEATHER-SUMMARY',
        'temperature': 'AIR-TEMPERATURE-DEGREES-F',
        'windBearing': 'WIND-BEARING-CW-DEGREES-FROM-N',
        'windGust': 'WIND-GUST-SPEED-MPH',
        'windSpeed': 'WIND-SPEED-MPH',
        }
    return {v: data['currently'].get(n, None) for n, v in fields.items()}


def _water_to_datetime(row):
    dt = datetime(
        year=round(row['YY']), month=round(row['MM']), day=round(row['DD']),
        hour=round(row['hh']), minute=round(row['mm']), tzinfo=UTC)
    return dt


def _water_to_dataframe(txt):
    stream = io.StringIO(re.sub(r' +', ' ', txt).replace('#', ''))
    data = pd.read_csv(stream, sep=' ', skiprows=[1])
    data.replace('MM', nan)
    return data


def _water_convert_type(val):
    if isinstance(val, np.float64):
        return float(val)
    elif isinstance(val, np.int64):
        return float(val)
    elif isinstance(val, str):
        if val == 'MM':
            return None 
        return float(val)
    else:
        # default case, do nothing 
        return val


def get_historical_water_conditions():
    """
    Retrieve historical water conditions data and cache as pickle

    Returns: dataframe, see get_water_conditions for column definitions
    """

    if os.path.isfile(BUOY_HISTORICAL):
        # read cached pickle
        with open(BUOY_HISTORICAL, 'rb') as fp:
            water_historical_data = pickle.load(fp)
    else:
        # parse raw sources
        sources = [
            os.path.join(DATA_DIR, '2014.txt'), 
            os.path.join(DATA_DIR, '2015.txt'),
            os.path.join(DATA_DIR, '2016.txt'),
            os.path.join(DATA_DIR, '2017.txt'),
            os.path.join(DATA_DIR, '2018-01.txt'),
            os.path.join(DATA_DIR, '2018-02.txt'),
            os.path.join(DATA_DIR, '2018-03.txt'),
            ]
        dfs = []
        for src in sources:
            with open(src, 'r') as fp:
                src_txt = fp.read()
            dfs.append(_water_to_dataframe(src_txt))
        water_historical_data = dfs[0].append(dfs[1:])
        water_historical_data.reset_index(drop=True, inplace=True)
        water_historical_data['DATETIME'] = water_historical_data.apply(_water_to_datetime, axis=1)
        # cache as pickle
        with open(BUOY_HISTORICAL, 'wb') as fp:
            pickle.dump(water_historical_data, fp)

    return water_historical_data


def get_water_conditions(dt, historical):
    """
    Retrieve observed water conditions at specified time
    
    Loads data from local pickle file, if available, else downloads from NOAA
    parses to a dataframe, and pickles it.
    
    Data come from the nearest NOAA station as historical and realtime (last
    45 days) datasets, formatted as tabular text files, see:
        http://www.ndbc.noaa.gov/station_page.php?station=44020
    
    Arguments:
        dt: datetime, timezone aware, observation time
        historical: dataframe containing historical water conditions data, as
            returned by get_historical_water_conditions(), included as an
            argument to avoid re-reading data from disk if this function is
            called multiple times
    
    Returns: dict with the following fields:
        WAVE-HEIGHT-METERS: Significant wave height (meters) is calculated as
            the average of the highest one-third of all of the wave heights
            during the 20-minute sampling period. See the Wave Measurements
            section.
        DOMINANT-WAVE-PERIOD-SECONDS: Dominant wave period (seconds) is the
            period with the maximum wave energy. See the Wave Measurements
            section.  AVERAGE-WAVE-PERIOD-SECONDS: Average wave period
            (seconds) of all waves during the 20-minute period. See the Wave
            Measurements section.
        DOMINANT-WAVE-DIRECTION-DEGREES-CW-FROM-N: The direction from which the
            waves at the dominant period (DPD) are coming. The units are
            degrees from true North, increasing clockwise, with North as 0
            (zero) degrees and East as 90 degrees. See the Wave Measurements
            section.
        WATER-TEMPERATIRE-DEGREES-C: Sea surface temperature (Celsius). For
            buoys the depth is referenced to the hull's waterline. For fixed
            platforms it varies with tide, but is referenced to, or near Mean
            Lower Low Water (MLLW).
    """
    # init times
    dt_utc = dt.astimezone(UTC)
    now_utc = datetime.now(tz=UTC)
    delta_days = (now_utc - dt_utc).days

    if delta_days <= 5:
        # retrieve hourly data for past 5 days
        url = 'http://www.ndbc.noaa.gov/data/5day2/{}_5day.txt'.format(BUOY_NUM)
        resp = requests.get(url)
        resp.raise_for_status()
        data = _water_to_dataframe(resp.text)
        data['DATETIME'] = data.apply(_water_to_datetime, axis=1)
    
    elif delta_days <= 45:
        # retrieve hourly data for past 45 days
        url = 'http://www.ndbc.noaa.gov/data/realtime2/{}.txt'.format(BUOY_NUM)
        resp = requests.get(url)
        resp.raise_for_status()
        data = _water_to_dataframe(resp.text)
        data['DATETIME'] = data.apply(_water_to_datetime, axis=1)

    else:
        data = historical

    # find the nearest record, should be within 2 hours
    time_diff = abs(dt_utc - data['DATETIME'])
    idx = time_diff.idxmin()
    rec = data.iloc[idx]
    logger.info('Closest water conditions record to {} is {}'.format(
                dt_utc, data.iloc[idx]['DATETIME']))

    # reformat resulting data
    fields = {  # NBDC names -> local names
        'WVHT': 'WAVE-HEIGHT-METERS',
        'DPD': 'DOMINANT-WAVE-PERIOD-SECONDS',
        'APD': 'AVERAGE-WAVE-PERIOD-SECONDS',
        'MWD': 'DOMINANT-WAVE-DIRECTION-DEGREES-CW-FROM-N',
        'WTMP': 'WATER-TEMPERATURE-DEGREES-C',
        }
    out = {v: _water_convert_type(rec[n]) for n, v in fields.items()}

    # set NA values
    na_values = {
        'WAVE-HEIGHT-METERS': 99,
        'DOMINANT-WAVE-PERIOD-SECONDS': 99,
        'AVERAGE-WAVE-PERIOD-SECONDS': 99,
        'DOMINANT-WAVE-DIRECTION-DEGREES-CW-FROM-N': 999,
        'WATER-TEMPERATURE-DEGREES-C': 99,
        }
    for key, val in na_values.items():
        if out[key] == val:
            out[key] == nan

    return out


def update(google_key, darksky_key, log_level):
    """
    Update all data in MV Polar Bears data sheet
    
    Arguments:
        google_key: path to Google API key file
        darksky_key: path to DarkSky API key file
        log_level: string, logging level, one of 'critical', 'error',
            'warning', 'info', 'debug'
    """
    lvl = getattr(logging, log_level.upper())
    logging.basicConfig(level=lvl)
    logger.setLevel(lvl)

    logger.info('Updating MV Polar Bears data sheet')
    client, doc, sheet = get_client(google_key) 
    add_missing_days(sheet)
    add_missing_dows(sheet)
    add_missing_weather(sheet, darksky_key)
    add_missing_water(sheet)
    logger.info('Update complete')


# command line interface
if __name__ == '__main__':

    # command line
    ap = argparse.ArgumentParser(
        description="Update data in MV Polar Bears data sheet",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('google_key', help="Path to Google API key file")
    ap.add_argument('darksky_key', help="Path to DarkSky API key file")
    ap.add_argument('--log_level', help='Log level to display',
                    choices=['critical', 'error', 'warning', 'info', 'debug'],
                    default='info')
    args = ap.parse_args()

    # run 
    update(args.google_key, args.darksky_key, args.log_level) 

