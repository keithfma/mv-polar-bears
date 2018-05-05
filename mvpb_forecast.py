"""
Fit forecast model to MV Polar Bears dataset and predict next day attendence
"""

from mvpb_util import get_client, read_sheet
import mvpb_data
from matplotlib import pyplot as plt
import pyflux as pf
import pandas as pd


# temporary
import pickle


# temporary constants, replace with arguments once wrapped as a function
GKEY = '~/.mv-polar-bears/google_secret.json'


# fetch data and do some post-processing
# client, doc, sheet = get_client(GKEY)
# data = read_sheet(sheet)
with open('delete_me.pkl', 'rb') as fp:
    data = pickle.load(fp)
data['GROUP'] = data['GROUP'].fillna(0)

# TEST 0: Plot the data
if False:
    plt.plot(data.index, data['GROUP'])
    plt.xlabel('Time')
    plt.ylabel('GROUP')
    plt.title('Polar Bears Attendence')
    plt.show()

if False:
    pd.plotting.autocorrelation_plot(data['GROUP'])
    plt.title('Polar Bears Attendence Autocorrelation')
    plt.show()

# TEST 1: ARIMA
if True:
    pass


