# -*- coding: utf-8 -*-
"""
Created on Mon Apr 23 07:28:37 2018

@author: keithfma
"""

import pickle
from copy import deepcopy


with open('delete_me.pkl', 'rb') as fp:
    content = pickle.load(fp)

def _parse_datetime(date_str, time_str):
    """Utility for parsing DATE and TIME columns to python datetime"""
    dt = dateutil.parser.parse(date_str + ' ' + time_str) 
    dt = dt.replace(tzinfo=US_EASTERN)
    return dt    

cid = {x: ii + 1 for ii, x in enumerate(content.columns)}
orig_dates = [_parse_datetime(content.iloc[r]['DATE'], content.iloc[r]['TIME']) for r in range(1, len(content))]
new_dates = deepcopy(orig_dates)

# NOTE: not clear that gspread and this func handle indices the same, be careful
def _insert_row(values, index, value_input_option):
    """Dummy for development on plane"""
    dt = dateutil.parser.parse(values[cid['DATE']] + ' ' + values[cid['TIME']])
    dt = dt.replace(tzinfo=US_EASTERN)
    new_dates.insert(index-3, dt)

# ensure minimum daily frequency by adding empty rows as needed
rid = 3 # 1-based index to google sheet row
prev_dt = _parse_datetime(content.iloc[1]['DATE'], content.iloc[1]['TIME'])
for ii in range(1, len(content)): # index to local copy
    row = row = content.iloc[ii]
    curr_dt = _parse_datetime(content.iloc[ii]['DATE'], content.iloc[ii]['TIME'])
    missing_days = (curr_dt - prev_dt).days - 1
    for jj in range(missing_days):
        day = prev_dt + timedelta(days=jj + 1)
        row_values = [nan] * len(content.columns)
        row_values[cid['DATE']] = day.strftime('%Y-%m-%d')
        row_values[cid['TIME']] = day.strftime('%H:%M %p')
        _insert_row(row_values, rid, 'USER_ENTERED')
        rid += 1
    prev_dt = curr_dt
    rid += 1
    
    