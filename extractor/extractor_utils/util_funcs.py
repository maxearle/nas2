import os
import numpy as np
from glob import glob

def check_path_existence(path: str) -> bool:
    return os.path.exists(path)

def is_nan_ignore_None(val) -> bool:
    """Convenience function to get around the fact that np.isnan gets confused if you throw it a None"""
    if val is None:
        return False
    elif np.isnan(val):
        return True
    else:
        return False
    
def dir_contains_ext(dirpath: str, ext: str) -> bool:
    file_list = glob(os.path.join(dirpath, f'*.{ext}'))
    return len(file_list) > 0

def writeline_in(filepath: str, line: str):
    with open(filepath,'w') as f:
        f.write(f"{line}{os.linesep}")