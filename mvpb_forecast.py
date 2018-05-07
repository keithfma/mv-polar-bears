"""
Fit forecast model to MV Polar Bears dataset and predict next day attendence
"""

from mvpb_util import get_client, read_sheet
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from arch import arch_model

# temporary
import pickle
from pdb import set_trace


# TODO: switch from printing to logging

# temporary constants, replace with arguments once wrapped as a function
GKEY = '~/.mv-polar-bears/google_secret.json'


def get_model(sheet):
    """
    Return GARCH model object including data and settings
    
    Arguments:
        sheet: gspread sheet connected to dataset
    """
    # client, doc, sheet = get_client(GKEY)
    # data = read_sheet(sheet)
    with open('delete_me.pkl', 'rb') as fp:
        data = pickle.load(fp)
    mod = arch_model(data['GROUP'].fillna(0).values, mean='ARX', lags=[1,3,5])
    return mod


def retrospective(sheet, disp=None):
    """
    Return retrospective forecast for all timesteps in dataset

    For each timestep, train the model on all prior data and perform 1-step
    forecast. The forecast returns both mean (expected value) and variance.

    Arguments:
        sheet: gspread sheet connected to dataset
        disp: int or None, interval for printing update message
    Returns: mean, std
        mean: forecasted mean value
        std: forecasted standard deviation
    """
    mod = get_model(sheet)

    # allocate results vectors
    num_data = len(mod.y)
    mean = np.zeros(num_data)
    mean[:] = np.nan
    std = np.zeros(num_data)
    std[:] = np.nan

    # perform retrospective forecast at all timesteps
    for ii in range(500, num_data):
        if disp and ii % disp == 0:
            print('Forecasting {} of {}'.format(ii, num_data))
        res = mod.fit(last_obs=ii+1, disp='off')
        frc = res.forecast(horizon=1)
        mean[ii] = frc.mean['h.1'][ii]
        std[ii] = np.sqrt(frc.variance['h.1'][ii])

    return mean, std


def tomorrow(sheet, disp=None):
    pass

# t = data.index.values
# plt.plot(t, grp, color='k')
# # plt.plot(t, mean, color='b')
# plt.fill_between(t, mean-std, mean+std, facecolor='b', alpha=0.5)
# plt.show()

# command line interface
if __name__ == '__main__':

    mean, std = retrospective(None, 10)

