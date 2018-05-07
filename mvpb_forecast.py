"""
Fit forecast model to MV Polar Bears dataset and predict next day attendence
"""

from mvpb_util import read_sheet
import pandas as pd
import numpy as np
from arch import arch_model
import logging


# init logging
logger = logging.getLogger('mv-polar-bears')


def get_model(data):
    """
    Return GARCH model object including data and settings
    
    Arguments:
        data: pandas Dataframe read from sheet
    """
    mod = arch_model(data['GROUP'].fillna(0).values, mean='ARX', lags=[1,3,5])
    return mod


# TODO: include some performance metric
def retrospective(data, first=500,  disp=100):
    """
    Return retrospective forecast for all timesteps in dataset

    For each timestep, train the model on all prior data and perform 1-step
    forecast. The forecast returns both mean (expected value) and variance.

    Arguments:
        data: pandas Dataframe read from sheet
        first: int, index of first timestep to forecast
        disp: int or None, interval for printing update message
    Returns: mean, std
        mean: forecasted mean value
        std: forecasted standard deviation
    """
    logger.info('Retrospective forecast')
    
    # prepare model
    mod = get_model(data)

    # allocate results vectors
    num_data = len(mod.y)
    mean = np.zeros(num_data)
    mean[:] = np.nan
    std = np.zeros(num_data)
    std[:] = np.nan

    # perform retrospective forecast at all timesteps
    for ii in range(first, num_data):
        if disp and ii % disp == 0:
            logger.info('Forecasting {} of {}'.format(ii, num_data))
        res = mod.fit(last_obs=ii+1, disp='off')
        frc = res.forecast(horizon=1)
        mean[ii] = frc.mean['h.1'][ii]
        std[ii] = np.sqrt(frc.variance['h.1'][ii])

    return mean, std


def tomorrow(data):
    """
    Return forecasted attendence for tomorrow

    Arguments:
        data: pandas Dataframe read from sheet
    Returns: mean, std
        mean: forecasted mean value
        std: forecasted standard deviation
    """
    logger.info('Tommorow forecast')

    mod = get_model(data)
    res = mod.fit(disp='off')
    frc = res.forecast(horizon=2)
    mean = frc.mean['h.2'].values[-1]
    std = np.sqrt(frc.variance['h.2'].values[-1])
    return mean, std

