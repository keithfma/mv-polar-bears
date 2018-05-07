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
data['GROUP'] = data['GROUP'].fillna(0)
data = data.fillna(method='backfill')
data['DAY_IDX'] = [int(x.strftime('%j')) for x in data.index]
data['WEEK_IDX'] = [int(x.strftime('%U')) for x in data.index]
data['TIME_IDX'] = range(len(data))

covars = {
    # 'AIR-TEMPERATURE-DEGREES-F': 10,
    # 'DAY_IDX': 20,
    # 'WEEK_IDX': 3,
    'TIME_IDX': 15,
    # 'PRECIP-PROBABILITY': 0.2,
    # 'WIND-SPEED-MPH': 10,
    # 'WAVE-HEIGHT-METERS': 1,
    }

x = data[list(covars.keys())].values
y = data['GROUP'].values
bw = list(covars.values())

predict = []
for ii in range(1, len(data)-1):
    print('{} of {}'.format(ii, len(data)))
    model = KernelReg(y[:ii], x[:ii,:], 'c'*len(covars), bw=bw)
    val = np.asscalar(model.fit(x[ii+1,:])[0])
    predict.append(val)


plt.plot(y[2:], label='truth', color='k');
plt.plot(predict, label='predict');
plt.legend();
plt.show()


