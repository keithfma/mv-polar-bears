"""
Fit forecast model to MV Polar Bears dataset and predict next day attendence
"""

from mvpb_util import get_client, read_sheet
import mvpb_data
from matplotlib import pyplot as plt
from statsmodels.nonparametric.kernel_regression import KernelReg
import pandas as pd
import numpy as np

# temporary
import pickle
from pdb import set_trace

# temporary constants, replace with arguments once wrapped as a function
GKEY = '~/.mv-polar-bears/google_secret.json'

# fetch data and do some post-processing
# client, doc, sheet = get_client(GKEY)
# data = read_sheet(sheet)
with open('delete_me.pkl', 'rb') as fp:
    data = pickle.load(fp)
data['GROUP0'] = data['GROUP'].fillna(0)
data = data.fillna(method='backfill')
data['DAY_IDX'] = [int(x.strftime('%j')) for x in data.index]
data['WEEK_IDX'] = [int(x.strftime('%U')) for x in data.index]
data['TIME_IDX'] = range(len(data))


# remove trend with kernel regression
covars = {
    'AIR-TEMPERATURE-DEGREES-F': 20,
    'DAY_IDX': 5,
    # 'WEEK_IDX': 3,
    # 'TIME_IDX': 10,
    # 'PRECIP-PROBABILITY': 0.5,
    # 'WIND-SPEED-MPH': 10,
    'WAVE-HEIGHT-METERS': 1,
    }

x = data[list(covars.keys())].values
y = data['GROUP0'].values
bw = list(covars.values())

model = KernelReg(y, x, 'c'*len(covars), bw=bw)
trend, junk = model.fit()

# plt.plot(y, label='truth', color='k');
# plt.plot(trend, label='trend');
# plt.legend();
# plt.show()

# # try modeling the residuals
# resid = y-trend
# 
# # crop data to in-season only
# in_season = np.array([False]*len(data))
# years = np.array([int(x.year) for x in data.index])
# for year in np.unique(years):
#     for idx, val in data['GROUP'].iteritems():
#         print(idx, val)
#     # year_data = [not pd.isnull(x) and y==year for x, y in zip(data['GROUP'], years)] 
#     # year_data = data['GROUP'][years==year]
#     # year_data = [not pd.isnull(x) and y==year for x, y in zip(data['GROUP'], years)] 
#     # year_data = [not pd.isnull(x) and y==year for x, y in zip(data['GROUP'], years)] 
#     # year_data = data['GROUP'][years==year]
#     # year_data = year_data.loc[-pd.isnull(year_data)]
#     # start_time = year_data.index[0]
#     # end_time = year_data.index[-1]
#     # start_idx = data.index.get_loc(start_time)
#     # end_idx = data.index.get_loc(end_time)
#     # in_season[start_idx:end_idx+1] = True
#     # print('{} - {}'.format(start_time, end_time))
#     # print('{} - {}'.format(start_idx, end_idx))
#     # print('---')


# # try a local model
# idx =729 
# rng = 15
# 
# # detrend with loess
# from statsmodels.nonparametric.smoothers_lowess import lowess
# 
# smooth = lowess(
#     endog=data['GROUP0'],
#     exog=data['DAY_IDX'],
#     frac=0.05, 
#     it=1,
#     return_sorted=False
#     )
# data['RESID'] = data['GROUP0'] - smooth
# 
# # get local data subset
# sub = data.iloc[idx-rng:idx+rng]


# TRY GARCH
from arch import arch_model

grp = data['GROUP0'].values
mod = arch_model(grp, mean='ARX', lags=[1,3,5])
res = mod.fit()
print(res.summary())
frc = res.forecast(start=4)

t = data.index.values
mean = frc.mean['h.1'].values
std = np.sqrt(frc.variance['h.1'].values)

plt.plot(t, grp, color='k')
plt.plot(t, mean, color='b')
plt.fill_between(t, mean-std, mean+std, facecolor='b', alpha=0.5)
plt.show()

# Works well over the fitted range -- Now try a rolling prediction...



# fig1 = plt.figure()
# plt.plot(resid, label='residuals')
# plt.title('Kernal Residuals')
# 
# from statsmodels.tsa.arima_model import ARIMA
# model = ARIMA(resid, order=(3,0,0))
# model_fit = model.fit(disp=0)
# print(model_fit.summary())
# # plot residual errors
# fig2 = plt.figure()
# residuals = pd.DataFrame(model_fit.resid)
# residuals.plot()
# plt.title('ARIMA Residuals')
# print(residuals.describe())
# 
# plt.show()

# rolling prediction
if False:
    predict = []
    for ii in range(1, len(data)-1):
        print('{} of {}'.format(ii, len(data)))
        model = KernelReg(y[:ii], x[:ii,:], 'c'*len(covars), bw=bw)
        # val = np.asscalar(model.fit(x[ii+1,:])[0])
        val = np.asscalar(model.fit(x[ii,:])[0])
        predict.append(val)


    plt.plot(y[2:], label='truth', color='k');
    plt.plot(predict, label='predict');
    plt.legend();
    plt.show()


