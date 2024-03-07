import nptdms as nt
import pandas as pd
import matplotlib.pyplot as plt
import logging
import numpy as np
from itertools import compress
from matplotlib.pyplot import cm
from scipy.ndimage import gaussian_filter
from scipy.optimize import curve_fit

def hist_bin(df,nbins):
        min = np.min(df)
        max = np.max(df)
        bin_spacing = (max-min)/nbins
        bin_lims = [[min + n*bin_spacing,min + (n+1)*bin_spacing] for n in np.arange(nbins)]
        count = np.array([np.count_nonzero((bin_lims[n][0] <= df) & (df < bin_lims[n][1])) for n in np.arange(nbins)])
        bin_mids = np.mean(bin_lims, axis = 1)
        return count, bin_mids, bin_spacing, bin_lims

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

def find_peak_lims(dt, peak_loc,strikes=1):
    strikes_total = 0
    lftdone = False
    lftdlt = 0
    lftlim = None
    lftlast = dt[peak_loc]
    lgrad = 0
    rgtdone = False
    rgtdlt = 0
    rgtlim = None
    rgtlast = dt[peak_loc]
    rgrad = 0
    #First find left limit
    while not lftdone:
        lftdlt += 1
        if peak_loc - lftdlt <= 0:
            lftlim = 0
            lftdone = True
        elif (dt[peak_loc-lftdlt] - dt[peak_loc-lftdlt+1]) == 0:
            continue
        else:
            lgradnew = (dt[peak_loc-lftdlt] - dt[peak_loc-lftdlt+1])/np.abs((dt[peak_loc-lftdlt] - dt[peak_loc-lftdlt+1]))
            if lgradnew*lgrad <0:
                strikes_total+=1
                if strikes_total >= strikes:
                    lftlim = peak_loc - lftdlt + 1 + strikes_total
                    lftdone = True
            else:
                strikes_total = 0
                lgrad = lgradnew

    strikes_total = 0
    
    #Finding right limit
    while not rgtdone:
        rgtdlt += 1
        if peak_loc + rgtdlt > (len(dt)-1):
            rgtlim = len(dt)-1
            rgtdone = True
        elif (dt[peak_loc+rgtdlt] - dt[peak_loc+rgtdlt-1]) == 0:
            continue
        else:
            rgradnew = (dt[peak_loc+rgtdlt] - dt[peak_loc+rgtdlt-1])/np.abs((dt[peak_loc+rgtdlt] - dt[peak_loc+rgtdlt-1]))
            if rgradnew*rgrad <0:
                strikes_total+=1
                if strikes_total >= strikes:
                    rgtlim = peak_loc + rgtdlt - 1 - strikes_total
                    rgtdone = True
            else:
                strikes_total = 0
                rgrad = rgradnew

    return np.max([lftlim - 1,0]), np.min([rgtlim + 1, len(dt) - 1])

def rle(inarray):
        """ run length encoding. Partial credit to R rle function. 
            Multi datatype arrays catered for including non Numpy
            returns: tuple (runlengths, startpositions, values) """
        ia = np.asarray(inarray)                # force numpy
        n = len(ia)
        if n == 0: 
            return (None, None, None)
        else:
            y = ia[1:] != ia[:-1]               # pairwise unequal (string safe)
            i = np.append(np.where(y), n - 1)   # must include last element posi
            z = np.diff(np.append(-1, i))       # run lengths
            p = np.cumsum(np.append(0, z))[:-1] # positions
            return(z, p, ia[i])

def find_most_persistent_value(indata, area_thresh=0.05, smoothing=1, n_bins = 100):
    cts, bin_mids, bin_spacing ,bin_lims= hist_bin(indata, n_bins)
    cts_smoothed = gaussian_filter(cts, sigma=1)
    hst_pks = get_persistent_homology(cts_smoothed)
    pklims = [find_peak_lims(cts_smoothed, hst_pks[n].born) for n in np.arange(len(hst_pks))] #Find peak lims for each peak in the histogram with the turn method
    ars = [np.trapz(cts[l:r]) if r < len(cts)-1 else np.trapz(cts[l:]) for l, r in pklims] #Get area of each peak using peak lims
    sig_ars_bool = ars > np.trapz(cts_smoothed)*area_thresh #Get a mask for peaks with areas representing greater than 10% of the total
    sig_pklims = list(compress(pklims, sig_ars_bool)) #Get corresponding significant peak lims

    max_run = np.array([])
    peaks = np.array([])
    for pair in sig_pklims:
        bools = np.logical_and((indata >= bin_lims[pair[0]][0]), (indata <= bin_lims[pair[1]][1]))
        rns = rle(bools)
        lns = rns[0][rns[2]]
        mx = np.max(lns)
        max_run = np.append(max_run,mx)
        cts_clipped = cts_smoothed
        cts_clipped[:pair[0]] = 0
        cts_clipped[pair[1]] =0
        peaks = np.append(peaks, np.argmax(cts_clipped))
    return [[bin_lims[sig_pklims[i][0]][0], bin_lims[sig_pklims[i][1]][1]] for i in np.arange(len(sig_pklims))], max_run, peaks, bin_mids, bin_spacing
if __name__ == "__main__":
    filename = r"F:\nanopores\2023_12_7\ch3\p3#\expt2_data\m13_1M_600_23-12-07_1554_007.tdms"
    file = nt.TdmsFile.read(filename)

    #Find channel containing samples
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

    def line(x, a, b):
                return a*x + b
    dt = data
    dt_x = np.arange(len(dt))
    value_persistence = find_most_persistent_value(dt,area_thresh=0)
    print(value_persistence)
    bsln_range = value_persistence[0][np.argmax(value_persistence[1])]
    bsln_peak = value_persistence[2][np.argmax(value_persistence[1])]
    peak_val = value_persistence[3][int(bsln_peak)]
    bsln_mask = np.abs(dt - peak_val) < 2*value_persistence[4]
    bsln_x = np.arange(len(dt))[bsln_mask]
    bsln_y = dt[bsln_mask]
    popt, _ = curve_fit(line, bsln_x, bsln_y)

    corrected_data = dt - line(dt_x, *popt)
    
    fig1,ax1 = plt.subplots()
    ax1.plot(data)
    ax1.plot(np.arange(len(data)),line(np.arange(len(data)),*popt))
    plt.show()