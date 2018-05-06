"""
Fit forecast model to MV Polar Bears dataset and predict next day attendence
"""

from mvpb_util import get_client, read_sheet
import mvpb_data
from matplotlib import pyplot as plt
import pyflux as pf
import pandas as pd
from statsmodels.nonparametric.smoothers_lowess import lowess


# temporary
import pickle
from pdb import set_trace


# temporary constants, replace with arguments once wrapped as a function
GKEY = '~/.mv-polar-bears/google_secret.json'


# TODO: need to fit to only the seasons themselves, otherwise precip etc become meaningless

# fetch data and do some post-processing
# client, doc, sheet = get_client(GKEY)
# data = read_sheet(sheet)
with open('delete_me.pkl', 'rb') as fp:
    data = pickle.load(fp)
# data['AIRTEMP'] = data['AIR-TEMPERATURE-DEGREES-F']
# data['WATERTEMP'] = data['WATER-TEMPERATURE-DEGREES-C']
# data['PRECIP'] = data['PRECIP-PROBABILITY']
# data['WAVE'] = data['WAVE-HEIGHT-METERS']
# data['WIND'] = data['WIND-SPEED-MPH']
# data['HUMID'] = data['HUMIDITY-PERCENT']
data['WOY'] = [int(x.strftime('%U')) for x in data.index]
data['DOY'] = [int(x.strftime('%j')) for x in data.index]
data['GROUP0'] = data['GROUP'].fillna(0)
data['INDEX'] = range(len(data))


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

# TEST 1: ARIMAX
if False:
    arimax = pf.ARIMAX(
        data, ar=2, integ=0, ma=2, family=pf.Normal(),
        formula='GROUP0 ~ WOY + AIRTEMP + WAVE')
    res = arimax.fit(method='MLE')
    arimax.plot_fit(intervals=True)

# TEST 2: model only in-season, otherwise predict 0
if False:
    season_doys = data['DOY'][-pd.isnull(data['GROUP'])]
    season_start_doy = min(season_doys)
    season_end_doy = max(season_doys)
    season_data = data[data['DOY'] >= season_start_doy]
    season_data = season_data[season_data['DOY'] <= season_end_doy]

    arimax = pf.ARIMAX(
        season_data, ar=1, integ=0, ma=1, family=pf.Normal(),
        formula='GROUP0 ~ WOY + AIRTEMP + WIND')
    res = arimax.fit(method='MLE')
    arimax.plot_fit(intervals=True)

# TEST 3: rolling predictions and errors
if False:
    predict = []
    for ii in range(20, len(data)-1):
        print('{} of {}'.format(ii, len(data)))
        curr = data.iloc[:ii]
        model = pf.ARIMAX(
            curr, ar=2, integ=0, ma=2, family=pf.Normal(),
            formula='GROUP0 ~ WOY + AIRTEMP + WAVE')
        model.fit(method='MLE')
        predict.append(model.predict(h=1, oos_data=data.iloc[ii+1]))

# Test 4; Remove nonparametric mean
if False:
    x = data['DOY'].tolist()
    y = data['GROUP0'].tolist()
    s = lowess(y, x, frac=0.1, it=0)

    sx = s[:,0]
    sy = s[:,1]
    plt.scatter(x, y)
    plt.plot(sx, sy, color='k')
    plt.show()

if False:
    x = [x.timestamp() for x in data.index]
    y = data['GROUP0'].tolist()
    s = lowess(y, x, frac=0.1, it=0)

    sx = s[:,0]
    sy = s[:,1]
    plt.scatter(x, y)
    plt.plot(sx, sy, color='k')
    plt.show()


if False:
    from sklearn.preprocessing import StandardScaler 
    from sklearn.svm import SVR

    # # get rows where GROUP is not null
    # data = data.loc[-pd.isnull(data['GROUP'])]

    # S = data[['AIR-TEMPERATURE-DEGREES-F', 'PRECIP-PROBABILITY', 'WIND-SPEED-MPH', 'WAVE-HEIGHT-METERS', 'DOY', 'WOY']]
    S = data[['DOY', 'WOY']]
    S = S.fillna(method='backfill').values
    sc_S = StandardScaler()
    S2 = sc_S.fit_transform(S)

    t = data['GROUP'].fillna(0).values
    t = t.reshape((len(t), 1))

    regressor = SVR(kernel = 'rbf')
    regressor.fit(S2, t)

    out = regressor.predict(S2)

# Just use loess
if False:
    x = data['DOY'].tolist()
    y = data['GROUP0'].tolist()
    s = lowess(y, x, frac=0.025, it=0)

    sx = s[:,0]
    sy = s[:,1]
    plt.scatter(x, y)
    plt.plot(sx, sy, color='k')
    plt.show()

# Try kernel regression - Works well! Key is to include INDEX, which makes this like a timeseries predictor
# TODO: clean up 
# TODO: write this in a loop to to next-step prediction and assess results
from statsmodels.nonparametric.kernel_regression import KernelReg

# x = data[['AIR-TEMPERATURE-DEGREES-F', 'PRECIP-PROBABILITY', 'WIND-SPEED-MPH', 'WAVE-HEIGHT-METERS', 'DOY', 'WOY']].fillna(method='backfill').values
x = data[['AIR-TEMPERATURE-DEGREES-F',  'DOY', 'INDEX', 'PRECIP-PROBABILITY', 'WIND-SPEED-MPH', 'WAVE-HEIGHT-METERS']].fillna(method='backfill').values

# x = data[['DOY', 'AIR-TEMPERATURE-DEGREES-F', 'WAVE-HEIGHT-METERS', 'WIND-SPEED-MPH']].fillna(method='backfill').values
# x = data['DOY'].fillna(method='backfill').values

# x = x.reshape((2, len(data)))
# x = []
# x.append(data['DOY'].values)
# x.append(data['WOY'].values)


y = data['GROUP'].fillna(0).values
# y = y.reshape((1, len(y)))

model = KernelReg(y, x, 'cccccc', bw=[10, 5, 10, 0.2, 10, 1])
# model = KernelReg(y, x, 'c', bw=[3])
out = model.fit()

plt.plot(range(len(data)), data['GROUP0'])
plt.plot(range(len(data)), out[0])
plt.show()
