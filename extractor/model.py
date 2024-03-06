from glob import glob
import os
import numpy as np
import nptdms as nt
import pandas as pd
import h5py as h
from scipy.optimize import curve_fit
import logging
from itertools import compress
import platform
import time
from scipy.ndimage import gaussian_filter1d
from extractor_utils.adv_baseline_fixing import find_most_persistent_value

class BadIndex(Exception):
    def __init__(self, *args):
        super().__init__(self,*args)

class ReachedEnd(Exception):
    def __init__(self, *args):
        super().__init__(self,*args)

def get_file_creation_time_epoch(path: str):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return os.path.getctime(path)
    else:
        stat = os.stat(path)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime

def hist_bin(df,nbins):
    try:
        min = np.min(df)
        max = np.max(df)
    except:
        logging.info(f"Failed to do hist_bin for data {df}")
    bin_spacing = (max-min)/nbins
    bin_lims = [[min + n*bin_spacing,min + (n+1)*bin_spacing] for n in np.arange(nbins)]
    count = np.array([np.count_nonzero((bin_lims[n][0] <= df) & (df < bin_lims[n][1])) for n in np.arange(nbins)])
    bin_mids = np.mean(bin_lims, axis = 1)
    return count, bin_mids, bin_spacing

class Peak:
    def __init__(self, startidx):
        self.born = self.left = self.right = startidx
        self.height = None
        self.died = None

    def get_height(self, seq):
        return float("inf") if self.died is None else seq[self.born] - seq[self.died]
    
    def get_persistence(self):
        return float("inf") if self.died is None else self.born-self.died
    
    def get_area(self, seq):
        return np.sum(seq[self.left:self.right])
    
    def __repr__(self):
        return f"Peak<Left: {self.left}, Right: {self.right}>"

def get_persistent_homology(seq):
    peaks = []
    # Maps indices to peaks
    idxtopeak = [None for s in seq]
    # Sequence indices sorted by values
    indices = range(len(seq))
    indices = sorted(indices, key = lambda i: seq[i], reverse=True)

    # Process each sample in descending order
    for idx in indices:
        lftdone = (idx > 0 and idxtopeak[idx-1] is not None)
        rgtdone = (idx < len(seq)-1 and idxtopeak[idx+1] is not None)
        il = idxtopeak[idx-1] if lftdone else None
        ir = idxtopeak[idx+1] if rgtdone else None

        # New peak born
        if not lftdone and not rgtdone:
            peaks.append(Peak(idx))
            idxtopeak[idx] = len(peaks)-1

        # Directly merge to next peak left
        if lftdone and not rgtdone:
            peaks[il].right += 1
            idxtopeak[idx] = il

        # Directly merge to next peak right
        if not lftdone and rgtdone:
            peaks[ir].left -= 1
            idxtopeak[idx] = ir

        # Merge left and right peaks
        if lftdone and rgtdone:
            # Left was born earlier: merge right to left
            if seq[peaks[il].born] > seq[peaks[ir].born]:
                peaks[ir].died = idx
                peaks[il].right = peaks[ir].right
                idxtopeak[peaks[il].right] = idxtopeak[idx] = il
            else:
                peaks[il].died = idx
                peaks[ir].left = peaks[il].left
                idxtopeak[peaks[ir].left] = idxtopeak[idx] = ir


    # This is optional convenience
    return sorted(peaks, key=lambda p: p.get_height(seq), reverse=True)

class TdmsDir():
    """ Class handling the reading of TDMS files in a directory, so that they can all be accessed with one object."""
    def __init__(self, root_directory: str):
        self.file_list = sorted(glob(os.path.join(root_directory, '*.tdms')))
        self.current_file = None

    def load_file_data(self, index: int | None = None):
        """Reads the current file if no index is provided, otherwise the specified file."""
        if index is None:
            file = nt.TdmsFile.read(self.file_list[self.current_file])
        elif index + 1 > len(self.file_list):
            raise BadIndex(f"Index {index} is invalid for TdmsDir of length {len(self.file_list)}")
        else:
            file = nt.TdmsFile.read(self.file_list[index])
        grp = file.groups()[0]
        found = False
        for chan in grp.channels():
            if len(chan) > 0:
                dchan = chan
                found = True
                break
        if not found:
            raise Exception("Couldn't find data channel.")
        data = dchan[:]
        return data

    def goto_file(self,index: int):
        """Changes file index to the stated one and reads its data."""
        self.current_file = index

    def set_file_index(self,index):
        if index + 1 > len(self.file_list):
            raise BadIndex(f"Index {index} is invalid for TdmsDir of length {len(self.file_list)}")
        else:
            self.current_file = index

    def next_file(self):
        if self.current_file == None:
            self.set_file_index(0)
        else:
            try:
                self.set_file_index(self.current_file + 1)
            except BadIndex:
                raise ReachedEnd("Reached end of file list, can't increment file index.")
        
    def get_file_name(self):
        return self.file_list[self.current_file]
    
    def __getitem__(self, subscript: int):
        self.goto_file(subscript)
        return self.load_file_data()
    
    def __len__(self):
        return len(self.file_list)

class Model():
    def __init__(self):
        self.tdms = None
        self.current_data = None
        self.corrected_data = None
        self.event_boundaries = None
        self.current_event_index = None
        self.event_data = None
        self.output_dt = None
        self.output_df = None

    def open_tdms_dir(self, fpath):
        self.tdms = TdmsDir(fpath)

    def check_path_existence(self,path: str):
        return os.path.exists(path)

    def gen_timescale(self, data: np.ndarray, sample_rate: int):
        return np.arange(len(data))/sample_rate

    def make_output_file(self,path):
        if self.check_path_existence(path):
            os.remove(path)
            logging.info("File already exists, deleting to replace with new one.")
        self.output = h.File(path, 'a', track_order=True)

    def add_group(self, grp: str, attrs: dict | None = None):
        self.output.create_group(grp, track_order=True)
        if attrs is None:
            return
        for key, value in attrs.items():
            self.output[grp].attrs[key] = value

    def create_dataset(self, grp: str, name: str,  data: np.ndarray, attrs: dict | None = None):
        self.output[grp].create_dataset(name, data=data, track_order=True)
        if attrs is None:
            pass
        else:
            for key, value in attrs.items():
                self.output[grp][name].attrs[key] = value

    def add_to_df(self, attrs: dict):
        new_row = pd.DataFrame([pd.Series(attrs, index = list(attrs.keys()))])
        if self.output_df is None:
            self.output_df = pd.concat([pd.DataFrame(),new_row], ignore_index=True)
        else:
            self.output_df = pd.concat([self.output_df, new_row], ignore_index=True)
        logging.info("New row successfully added to dataframe.")
        
    def next_file(self):
        self.tdms.next_file()
        self.current_data = self.tdms.load_file_data()
        self.bsln = None
        self.noise = None

    def slope_fix_hist_method(self, data):
        def line(x, a, b):
            return a*x + b
        xdata = np.arange(len(data))
        counts, bin_pos, spc = hist_bin(data,50)
        hist_peaks = get_persistent_homology(counts)
        areas = np.array([hist_peaks[n].get_area(counts)/(np.sum(counts)) for n in np.arange(len(hist_peaks))])
        selected = [areas[n]>0.1 for n in np.arange(len(areas))]
        sel_peaks = list(compress(hist_peaks,selected))
        most_sig = sel_peaks[:2]
        levels_by_depth = [bin_pos[sorted(most_sig,key=lambda p: bin_pos[p.born],reverse=True)[n].born] for n in np.arange(len(most_sig))]
        try:
            bsln_level = levels_by_depth[0]
        except:
            popt, pcov = curve_fit(line, xdata, data)
            return (data - line(xdata,*popt), pcov)
        mask = np.abs((data - bsln_level)) < 0.03
        popt, pcov = curve_fit(line, xdata[mask], data[mask])
        return (data - line(xdata,*popt), pcov)
    
    def slope_fix_average_run_method(self, leeway):
        """Fix current data slope using average run length method"""
        def line(x, a, b):
            return a*x + b
        dt = self.current_data
        dt_x = np.arange(len(dt))
        value_persistence = find_most_persistent_value(dt,area_thresh=0)
        bsln_range = value_persistence[0][np.argmax(value_persistence[1])]
        bsln_mask = np.logical_and(dt > bsln_range[0], dt < bsln_range[1])
        bsln_x = np.arange(len(dt))[bsln_mask]
        bsln_y = dt[bsln_mask]
        popt, _ = curve_fit(line, bsln_x, bsln_y)

        self.corrected_data = dt - line(dt_x, *popt)
        self.bsln = np.mean(bsln_y)
        self.noise = np.std(bsln_y)

    def gen_event_attrs(self, name: str, berth: int, sample_rate: float) -> dict:
        cropped_event = self.event_data[berth:-(berth-1)]
        logging.debug(f"Generating event attrs for cropped event of length {len(cropped_event)}")
        c_e_l = len(cropped_event)
        c_e_a = np.trapz(cropped_event)
        attrs = {
            'name':name,
            "samples":c_e_l,
            "duration_s":c_e_l/sample_rate,
            "ecd":c_e_a/sample_rate,
            "mean":np.mean(cropped_event),
            "ffap":np.trapz(cropped_event[:(c_e_l)//5])/c_e_a,
            "lfap":np.trapz(cropped_event[(-(c_e_l)//5):])/c_e_a,
            "skew":np.trapz(cropped_event*np.linspace(0,1,len(cropped_event)))/np.trapz(cropped_event*np.linspace(1,0,len(cropped_event))),
            "event_timestamp_s":int(os.path.getmtime(self.tdms.get_file_name())),
            "trace_baseline_nA":self.bsln
        }
        try:
            attrs["linearity"] = np.sqrt(np.sum(np.diag(self.slope_fix(cropped_event)[1])))
        except:
            logging.debug("Couldn't find linearity for this event, assigning NaN")
            attrs["linearity"] = np.nan

        return attrs

    def correct_slope(self):
        self.current_data = self.slope_fix(self.current_data)[0]

    def update_event_boundaries(self, thresh: float, tol: int):
        def get_lims(hits):
            runs = np.diff(hits)
            lims = np.where(runs > 1)[0]
            limits = []
            for i in np.arange(len(lims) + 1):
                if i == 0:
                    left = hits[0]
                try:
                    right = hits[lims[i]]
                    limits.append([left, right])
                    left = hits[lims[i]+1]
                except IndexError:
                    right = hits[-1]
                    limits.append([left, right])
            return limits
        def merge(list, dist = 100):
            pairs = list.copy()
            space = np.array([pairs[i+1][0] - pairs[i][1] for i in np.arange(len(pairs) - 1)])
            merge_locs = np.where(space > dist)[0].astype(int)
            if len(merge_locs) == 0:
                return pairs
            new_list = []
            for i, loc in enumerate(merge_locs):
                if i == 0:
                    left = pairs[0][0]
                try:
                    right = pairs[loc][1]
                    new_list.append([left, right])
                    left = pairs[loc + 1][0]
                except IndexError:
                    right = pairs[-1][1]
                    new_list.append([left, right])
            return new_list
        hits = np.where(self.corrected_data < thresh)[0]
        if len(hits) == 0:
            self.event_boundaries = []
            self.current_event_index = None
            return
        lims = get_lims(hits)
        logging.debug(f"Lims are: {lims}")
        merged = merge(lims, tol)
        logging.debug(f"Merged lims are: {merged}")
        self.event_boundaries = merged
        self.current_event_index = None

    def next_event(self, berth: int):
        if self.current_event_index is None:
            self.current_event_index = 0
        else:
            self.current_event_index += 1
        logging.info(f"Selected event {self.current_event_index + 1} of {len(self.event_boundaries)}")
        try:
            curr_event_boundaries = self.event_boundaries[self.current_event_index]
            logging.debug("Index valid, updating boundaries")
            self.event_data = self.corrected_data[(curr_event_boundaries[0] - berth):(curr_event_boundaries[1] + berth)]
            try:
                bsln_fixed = self.fix_event_baseline(berth)
                self.event_data = bsln_fixed
            except:
                #TODO
                pass
        except IndexError:
            logging.debug("Invalid event boundary selected")
            self.event_data = np.nan
            raise EventError("Run out of events for this batch.")
        logging.debug(f"Event boundaries are {curr_event_boundaries}")

    def fix_event_baseline(self, berth: int):
        edata = self.event_data
        ebsln = np.mean([edata[:berth//2],edata[-berth//2:]])
        return edata - ebsln

class EventError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)       