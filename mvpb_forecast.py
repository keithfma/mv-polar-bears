"""
Fit forecast model to MV Polar Bears dataset and predict next day attendence
"""

from mvpb_util import get_client, read_sheet
import mvpb_data
import pickle


# temporary constants, replace with arguments once wrapped as a function
GKEY = '~/.mv-polar-bears/google_secret.json'


# fetch data from google sheet
# client, doc, sheet = get_client(GKEY)
# data = read_sheet(sheet)
with open('delete_me.pkl', 'rb') as fp:
    data = pickle.load(fp)
