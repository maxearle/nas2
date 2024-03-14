import pandas as pd
import h5py as h
import os
import logging
import numpy as np

def check_path_existence(path: str) -> bool:
    return os.path.exists(path)

def get_file_ext(path: str) -> str:
     _, ext = os.path.splitext(path)
     return ext

def straight_line(x, b, a):
    return b*x + a

def parse_pois(unparsed: str) -> dict:
    ws_removed = unparsed.replace(" ","")
    split_pairs = ws_removed.split(";")
    pairs = [split_pairs[i].split(",") for i in np.arange(len(split_pairs))]
    pois = {pairs[i][0]:int(pairs[i][1]) for i in np.arange(len(pairs))}
    return pois

def check_binary(test_str):
    allowed = set("01")
    return set(test_str).issubset(allowed)

class h5Data():
    def __init__(self, location, maingroup="current_data"):
        self._data_source = h.File(location,'r')
        self._main_group = self._data_source[maingroup]
        self._ds_names = self._main_group.keys()
        self.current_ds_index = None

    def __iter__(self):
        return self
    
    def __len__(self):
        return len(self._ds_names)
    
    def next_ds(self):
        if self.current_ds_index is None:
            self.current_ds_index = 0
        elif self.current_ds_index == len(self)-1:
            logging.info("Reached end of group. Can't select next dataset.")
        else:
            self.current_ds_index += 1

    def prev_ds(self):
        if self.current_ds_index == 0:
            logging.info("At first ds of group, can't select previous dataset.")
        else:
            self.current_ds_index -= 1

    def get_name(self, index):
        return self._ds_names[index]
    
    def get_names(self):
        return self._ds_names
    
    def close(self):
        self._data_source.close()

    def __next__(self):
        self.next_ds()
        if self.current_ds_index >= len(self):
            raise StopIteration
        else:
            return self
    
    def get_data(self, index):
        try:
            return self._main_group[self.get_name(index)]
        except:
            raise Exception(f"Could not retrieve data for index {index}.")
        
    def get_current_name(self):
        if self.current_ds_index is None:
            raise Exception("Current index is None.")
        elif self.current_ds_index >= len(self):
            raise Exception(f"{self.current_ds_index} is out of range.")
        else:
            return list(self._ds_names)[self.current_ds_index]
        
    def get_current_data(self):
        if self.current_ds_index is None:
            raise Exception("Current index is None.")
        elif self.current_ds_index >= len(self):
            raise Exception(f"{self.current_ds_index} is out of range.")
        else:
            return self._main_group[self.get_current_name()]
        
    def __getitem__(self, index):
        return self.get_data(index)
        
    def __repr__(self):
        return f"<h5Data Object with length {len(self)} and current index {self.current_ds_index}.>"

class Model():
    def __init__(self):
        self.hData = None
        self.df = None
        self.assignments = None
        self.pois = None

    def import_data(self, data_loc):
        self.hData = h5Data(data_loc)

    def import_df(self,df_loc):
        self.df = pd.read_pickle(df_loc)

    def query_df(self, query):
        return self.df.query(query)
    
    def set_pois(self, pois_dict):
        self.pois = pois_dict

    def close(self):
        self.hData.close()
        self.hData = None
    
    def _create_assignments_df(self):
        index = np.arange(len(self.hData))
        names = self.hData.get_names()
        assign = np.full((len(self.pois),len(self.hData)), None)
        self.assignments = pd.DataFrame(data=np.array([index,list(names),*assign]).T.tolist(), columns = ["index", "event_name", *self.pois.keys()])
        self.assignments = self.assignments.set_index('index')

    def change_assignments(self, index, new_ass):
        series = self.assignments.loc[index]
        self.assignments.loc[index] = pd.Series({'event_name':series["event_name"],**new_ass})

    def save_assignments(self,path):
        self.assignments.to_pickle(path)
