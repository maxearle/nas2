import pandas as pd
import h5py as h
import os

props_name = r"E:\max_data\data0\props2.pkl"
df = pd.read_pickle(props_name)

data_name = r"E:\max_data\data0\EVENTS.hdf5"
dirname = os.path.dirname(data_name)
props_text = os.path.splitext(os.path.basename(props_name))[0]
data_text = os.path.splitext(os.path.basename(data_name))[0]
new_file_path = os.path.join(dirname, f"{data_text}_from_{props_text}.hdf5")



with h.File(data_name, 'r') as old_file, h.File(new_file_path, 'w') as new_file:
    old_group = old_file["current_data"]
    old_group_attrs = old_group.attrs
    new_group = new_file.create_group("current_data")
    for tuple in old_group_attrs.items():
        new_group.attrs.create(tuple[0],tuple[1])
    for name in set(df["name"]):
        old_group.copy(old_file["current_data"][name],new_group)
