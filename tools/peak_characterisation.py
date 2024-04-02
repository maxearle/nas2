import h5py as h
import pandas as pd
import os
import numpy as np
import scipy.ndimage as spnd
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from itertools import compress
from matplotlib.pyplot import cm
import logging
import matplotlib as mpl

def line(x,a,b):
    return b*x + a

def hist_bin(df,nbins):
    min = np.min(df)
    max = np.max(df)
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

def peak_area(dt, peak_loc, lim):
    lftdone = False
    lftdlt = 0
    lftlim = None
    rgtdone = False
    rgtdlt = 0
    rgtlim = None
    #First find left limit
    while not lftdone:
        lftdlt += 1
        if peak_loc - lftdlt < 0:
            lftlim = 0
            lftdone = True
        elif np.abs(dt[peak_loc - lftdlt]) < lim:
            lftlim = peak_loc - lftdlt
            lftdone = True
    
    #Finding right limit
    while not rgtdone:
        rgtdlt += 1
        if peak_loc + rgtdlt > (len(dt)-1):
            rgtlim = len(dt)-1
            rgtdone = True
        elif np.abs(dt[peak_loc + rgtdlt]) < lim:
            rgtlim = peak_loc + rgtdlt
            rgtdone = True

    ar = np.sum(dt[lftlim:rgtlim])
    width = rgtlim - lftlim
    return (lftlim,rgtlim), width, ar

def peak_area_turn(dt, peak_loc,strikes=1):
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
    width = rgtlim - lftlim
    pdt = dt[lftlim:rgtlim+1]
    #All of the below only applies for negative peaks, does not work for positive peaks
    pdt1 = pdt - np.max(pdt)
    triangle_area = 0.5 * width * np.min([pdt1[0],pdt1[-1]])
    ar = np.trapz(pdt1) - triangle_area
    depth = np.min(pdt1)
    return (lftlim,rgtlim), width, ar, depth

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

    return lftlim, rgtlim

def characterise_peak(dt, lftlim, rgtlim):
    width = rgtlim - lftlim
    pdt = dt[lftlim:rgtlim+1]
    #All of the below only applies for negative peaks, does not work for positive peaks
    pdt1 = pdt - np.max(pdt)
    triangle_area = 0.5 * width * np.min([pdt1[0],pdt1[-1]])
    ar = np.trapz(pdt1) - triangle_area
    depth = np.min(pdt1)
    return width, ar, depth

#IDEAS:

font = {'weight' : 'normal',
        'size'   : 17}
mpl.rc('font',**font)
logging.basicConfig(level="INFO")
sig = 5
oversample_factor = 5
dialin = False
plot = False
data_location = r"C:\Users\me424\Desktop\casey\MS2 101 barcodes\cherrypicked-50-unfolded-Max\EVENTS.hdf5"

all_peaks_df = pd.DataFrame()
with h.File(data_location,'r') as f:
    grp = f["current_data"]
    sample_rate = grp.attrs["sample_rate"]
    n_datasets = len(grp)
    for i, ds in enumerate(grp):  

        logging.info(f"Doing {i+1}/{n_datasets}")
        #Make histogram of all points
        counts, bin_pos, spc = hist_bin(grp[ds][:],50)

        #Find peaks in histogram and calculate their area. Select those which represent a minimum percentage of the total area.
        hist_peaks = get_persistent_homology(counts)
        areas = np.array([hist_peaks[n].get_area(counts)/(np.sum(counts)) for n in np.arange(len(hist_peaks))])
        selected = [areas[n]>0.1 for n in np.arange(len(areas))]
        sel_peaks = list(compress(hist_peaks,selected))
        most_sig = sel_peaks[:2]
        levels_by_depth = [bin_pos[sorted(most_sig,key=lambda p: bin_pos[p.born],reverse=True)[n].born] for n in np.arange(len(most_sig))]


        #Calculate leeway from std of baseline
        dt = grp[ds][:]
        leeway = np.std(dt[np.abs((dt - levels_by_depth[0])) < 0.03])


        #Get points from DNA plateau
        dna_plat_pos = np.arange(len(dt))[np.abs((dt - levels_by_depth[1])) < sig*leeway]
        dna_plat_vals = dt[np.abs((dt - levels_by_depth[1])) < sig*leeway]

        #Fit line
        ppts, pcovs = curve_fit(line,dna_plat_pos,dna_plat_vals)


        #Extract points which are part of event plateau
        dt_levelled_plateau = dt-line(np.arange(len(dt)),*ppts)
        plat_ends = np.min(np.where(np.abs(dt_levelled_plateau) < leeway)),np.max(np.where(np.abs(dt_levelled_plateau) < leeway))
        dna_level = line(np.mean(plat_ends),*ppts) - levels_by_depth[0]
        plat_dt = dt_levelled_plateau[plat_ends[0]:plat_ends[1]]


        smoothed = spnd.gaussian_filter(plat_dt,sigma = oversample_factor)

        plat_peaks = get_persistent_homology(-smoothed)
        peak_lims = [find_peak_lims(smoothed,plat_peaks[n].born,2) for n in np.arange(len(plat_peaks))]
        peak_props = sorted([[(peak_lims[n]), *characterise_peak(plat_dt,*peak_lims[n])] for n in np.arange(len(peak_lims))], key=lambda p: -p[2], reverse=True)
        peak_props_normed = [(*peak_props[n],peak_props[n][-1]/dna_level) for n in np.arange(len(peak_props))]
        std_normed = 2*np.std(plat_dt) / dna_level

        #Make Df
        plat_df = pd.DataFrame()
        for p in peak_props_normed:
            name = ds
            plat_dur = len(plat_dt)
            peak_start_sample = plat_ends[0] + p[0][0]
            peak_end_sample = plat_ends[0] + p[0][1]
            end_dist_left = ((p[0][0]+p[0][1])/2)/plat_dur
            end_dist_right = 1 - end_dist_left
            start_end_offset = np.abs(plat_dt[p[0][0]] - plat_dt[p[0][1]])
            duration_rt = p[1]/sample_rate
            duration_rel = (p[1]/plat_dur)
            ecd = p[2]/sample_rate
            real_depth = p[3]
            rel_depth = p[4]
            row = pd.DataFrame([pd.Series(data=[name,peak_start_sample,peak_end_sample, end_dist_left,end_dist_right,start_end_offset,duration_rt,duration_rel,ecd,real_depth,rel_depth],
                                        index = ["name","peak_start","peak_end","left_dist","right_dist","st_end_offset_nA","duration_s","rel_duration","ecd_nA_s","depth_nA","rel_depth"])])
            plat_df = pd.concat([plat_df,row], ignore_index = True)

        #Filter duplicates
        plat_df_filt = plat_df.drop_duplicates(ignore_index = True).query("(rel_depth > -0.5*@std_normed) & (st_end_offset_nA < 0.1)")
        logging.info(plat_df_filt.head(10))


        all_peaks_df = pd.concat([all_peaks_df,plat_df_filt],axis=0,ignore_index=True)
        
        if plot:
            fig, axs = plt.subplots(1,3,figsize = (22,8),dpi=80)

            axs[0].set_title("All-Points Histogram for Event\n with Significant Peaks Labelled")
            axs[0].bar(np.arange(len(counts)),counts,width=1)
            axs[0].plot([hist_peaks[n].born for n in np.arange(4)],[counts[hist_peaks[n].born] for n in np.arange(4)],'ko')
            axs[0].set_xlabel("Counts")
            axs[0].set_ylabel("Occurrences")

            axs[1].set_title("Event with most significant levels \n 1x DNA Level Bounds and Plateau Fit Line")
            axs[1].plot(grp[ds][:])
            for p in sel_peaks:
                axs[1].axhline(bin_pos[p.born], alpha = 0.5,c='g')
            axs[1].axhline(bin_pos[sel_peaks[1].born] + sig*leeway,ls='--', alpha = 0.25)
            axs[1].axhline(bin_pos[sel_peaks[1].born] - sig*leeway,ls='--', alpha = 0.25)
            axs[1].plot(np.arange(len(dt)), line(np.arange(len(dt)),*ppts) + leeway,c='r',ls='--', alpha = 0.5)
            axs[1].plot(np.arange(len(dt)), line(np.arange(len(dt)),*ppts) - leeway,c='r',ls='--', alpha = 0.5)
            axs[1].plot(np.arange(len(dt)), line(np.arange(len(dt)),*ppts),c='r', alpha = 0.5)
            axs[1].set_xlabel("Samples")
            axs[1].set_ylabel("Current /nA")

            cols_needed = len(plat_df_filt)
            color = iter(cm.rainbow(np.linspace(0, 1, cols_needed)))
            axs[2].set_title("Event Plateau Smoothed\n with Significant Peaks Shaded")
            axs[2].plot(plat_dt)
            for i,p in plat_df_filt.iterrows():
                c = next(color)
                plat_end_left = plat_ends[0]
                pl = p.peak_start - plat_end_left
                pr = p.peak_end - plat_end_left  
                baseline_grad = (plat_dt[pr]-plat_dt[pl])/(pr-pl)
                baseline_int = plat_dt[pl]-baseline_grad * pl
                peak_baseline = line(np.arange(pl,pr+1),baseline_int,baseline_grad)
                axs[2].fill_between(np.arange(pl,pr + 1),peak_baseline,plat_dt[pl:pr+1],fc=c)
            axs[2].set_xlabel("Samples")
            axs[2].set_ylabel("Current /nA")
            fig.tight_layout()

            plt.show()
        if dialin:
            break
dirname = os.path.dirname(data_location)
file_text = os.path.splitext(os.path.basename(data_location))[0]
new_file_path = os.path.join(dirname, f"all_peaks_from_{file_text}.pkl")
all_peaks_df.to_pickle(new_file_path)
