"""
LEGACY:
Was previously used to turn attrs attached to datasets in an hdf5 into a dataframe for use with multi-filter.
"""

import pandas as pd
import numpy as np
import h5py
import os

fname = r"C:\Users\me424\Desktop\gdata1\EVENTS.hdf5"
file = h5py.File(fname, 'r')

data = file["current_data"]
sets = list(data.keys())

df = pd.DataFrame()
for set in data:
    props = dict(data[set].attrs)
    row = pd.DataFrame([pd.Series(data = [set,*props.values()], index = ["name", *props.keys()])])
    df = pd.concat([df, row], ignore_index = True)

root = os.path.dirname(fname)

df.to_pickle(os.path.join(root, "props.pkl"))