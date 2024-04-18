import pandas as pd
import h5py
import os
import logging
import numpy as np

class BadIndex(Exception):
    pass

def check_path_existence(path: str) -> bool:
    return os.path.exists(path)

def diff_dfs(df1,df2):
    if df1 is None:
        return df2
    elif df2 is None:
        return df1
    return pd.concat([df1,df2]).drop_duplicates(keep=False)

def union_dfs(df1,df2):
    if df1 is None:
        return df2
    elif df2 is None:
        return df1
    return pd.concat([df1,df2]).drop_duplicates(keep='first')

def remove_bad_values(array: np.ndarray) -> np.ndarray:
    return array[np.isfinite(array)]

def get_file_ext(path: str) -> str:
     _, ext = os.path.splitext(path)
     return ext

def get_line(point1: 'Point', point2: 'Point') -> tuple[float, float]:
    grad = (point2.y - point1.y)/(point2.x - point1.x)
    intercept = point1.y - point1.x * grad
    return (grad, intercept)

def get_distance(pt1: 'Point', pt2: 'Point') -> float:
    return np.sqrt((pt2.x-pt1.x)**2 + (pt2.y-pt1.y)**2)

def get_nearest(df: pd.DataFrame, params: tuple[str,str], pt: 'Point') -> pd.DataFrame:
    for i, row in enumerate(df.iterrows()):
        rowPt = Point(float(row[1][params[0]]), float(row[1][params[1]]))
        dist = get_distance(pt, rowPt)

        if i == 0:
            closest = i
            closest_dist = dist
            continue

        if dist < closest_dist:
            closest = i
            closest_dist = dist
    
    return df.iloc[closest,:]

def straight_line(x, b, a):
    return b*x + a

def isbelow(pt: 'Point', line_vars: tuple[float,float]) -> bool:
    return pt.y < (pt.x * line_vars[0] + line_vars[1])


class Point():
    """Simple point class"""
    x: float | None
    y: float | None
    def __init__(self, x = None, y = None):
        self.x = x
        self.y = y

class Model():
    df: pd.DataFrame | None = None
    selection: pd.DataFrame | None = None
    current: pd.DataFrame | None = None
    data: h5py.File | None = None
    name_column_index: int | None = None
    def __init__(self):
        self.point1 = Point()
        self.point2 = Point()
        self.region_point = Point()

    def open_hdf5(self, file_name: str):
        self.data = h5py.File(file_name, 'r')

    def open_df(self, file_name: str):
        self.df = pd.read_pickle(file_name)

    def get_sample_rate(self) -> int:
        return self.data['current_data'].attrs['sample_rate']
    
    def get_event_data(self, name: str) -> np.ndarray:
        return self.data['current_data'][name][:]
    
    def get_df_cols(self, exclude: int | None = None) -> list[str]:
        if exclude is None:
            return list(self.df.columns)
        else:
            return list(self.df.iloc[:,:exclude].columns) + list(self.df.iloc[:,(exclude + 1):].columns)
        
    def choose_event(self, click_loc: Point, params: tuple[str,str], tol = 0.02) -> dict | None:
            #Condition data by removing non-finite values
            x_data = np.array(self.df[params[0]])
            x_data_wo_bad_values = remove_bad_values(x_data)
            y_data = np.array(self.df[params[1]])
            y_data_wo_bad_values = remove_bad_values(y_data)

            #Work out range of values eligible for shortlist
            full_param_ranges = (np.ptp(x_data_wo_bad_values), np.ptp(y_data_wo_bad_values))
            param_ranges = ((click_loc.x - tol*full_param_ranges[0], click_loc.x + tol*full_param_ranges[0]),
                            (click_loc.y - tol*full_param_ranges[1], click_loc.y + tol*full_param_ranges[1]))
            
            #First deal with nans
            dfInfToNan = self.df.replace([np.inf, -np.inf], np.nan, inplace=False).infer_objects(copy=False)
            conditionedDf = dfInfToNan.dropna(subset = [params[0],params[1]], how = 'all')

            #Then select shortlist
            subDf1 = conditionedDf.query(f"{params[0]} > {param_ranges[0][0]} & {params[0]} < {param_ranges[0][1]}")
            subDf2 = subDf1.query(f"{params[1]} > {param_ranges[1][0]} & {params[1]} < {param_ranges[1][1]}")

            if len(subDf2) == 0:
                return None
            
            event_props = get_nearest(subDf2, params, click_loc)
            return event_props
    def get_sub_df(self, click_loc: Point, params: tuple[str,str], line_vars = tuple[float,float]):

        #First deal with nans
        dfInfToNan = self.df.replace([np.inf, -np.inf], np.nan, inplace=False)
        conditionedDf = dfInfToNan.dropna(subset = [params[0],params[1]], how = 'all')

        if isbelow(click_loc, line_vars):
            subDf = conditionedDf.query(f"{params[1]} < ({params[0]}*{line_vars[0]} + {line_vars[1]})")
            logging.info("Returning sub-df for points below split line.")
            return subDf
        else:
            subDf = conditionedDf.query(f"{params[1]} > ({params[0]}*{line_vars[0]} + {line_vars[1]})")
            logging.info("Returning sub-df for points below split line.")
            return subDf
        


