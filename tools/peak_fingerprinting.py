import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import itertools
import h5py as h
import os

def gen_fp(locs,indices=None):
    if indices is None:
        ns = np.arange(len(locs))
    else:
        ns = indices
    return np.array([[locs[n] - locs[i] for i in ns] for n in ns])

def fp_loss(ideal_peak_locs, peak_locs):
    def loss(fp1, fp2):
        #Calculate loss (Euclidean distance) between fp2 and fp1
        return np.sqrt(np.sum(np.array([(fp1[n]-fp2[n])**2 for n in np.arange(len(fp2))])))
    
    if len(peak_locs) >= len(ideal_peak_locs):
        peak_combs = list(itertools.combinations(np.arange(len(peak_locs)),len(ideal_peak_locs)))
    else:
        peak_combs = [np.arange(len(peak_locs))]
    lowest_loss = None
    best_perm = np.arange(len(ideal_peak_locs))
    best_comb_ideal = np.arange(len(ideal_peak_locs))
    best_comb_peak = None
    c=0
    for pcomb in peak_combs:
        c+=1
        print(f"Handling peak combination {c} of {len(peak_combs)}")
        fp_nos_perms = list(itertools.permutations(pcomb))
        for perm in fp_nos_perms:
            perm_locs = [peak_locs[n] for n in perm]
            perm_fp = gen_fp(perm_locs)
            id_peak_nos_combos = list(itertools.combinations(np.arange(len(ideal_peak_locs)),len(perm_locs)))
            for comb in id_peak_nos_combos:
                for sign in (+1,-1):
                    sub_id_fp = gen_fp(ideal_peak_locs,comb)
                    loss_total = np.sqrt(np.sum([loss(sub_id_fp[n],sign*perm_fp[n])**2 for n in np.arange(len(perm_fp))]))
                    if lowest_loss is None:
                        lowest_loss = loss_total
                        best_perm = perm
                        best_comb_ideal = comb
                    elif loss_total < lowest_loss:
                        lowest_loss = loss_total
                        best_perm = perm
                        best_comb_ideal = comb

    return best_perm, best_comb_ideal, lowest_loss


df_loc = r"f:\npore_data\2024_01_24\ch3\p8\dataproxdist2\all_peaks_from_events_from_props73.pkl"
df = pd.read_pickle(df_loc)

dt_loc = r"f:\npore_data\2024_01_24\ch3\p8\dataproxdist2\events_from_all_peaks_from_events_from_props73.hdf5"

ideal_peak_positions = ideal = [29/190, 43/190, 62/190, 84/190, 106/190, 128/190, 158/190]
event_names = set(df.name)
plot = False

new_df = pd.DataFrame()
ce = 0
with h.File(dt_loc,'r') as dt:
    for event in event_names:
        ce += 1
        print(f"Doing event {ce} of {len(event_names)}")
        event_dt = dt['current_data'][event][:]
        sub_df = df.query("name == @event")
        peak_locs = list(sub_df["left_dist"])
        print(f"Peak locs: {len(peak_locs)}")
        best_perm,best_icomb, loss = fp_loss(ideal_peak_positions,peak_locs)
        print(f"perm: {best_perm}, icomb: {best_icomb}, loss:{loss}")
        ordered = [x for _,x in sorted(zip(best_perm,best_icomb))]
        print(sub_df)
        peaks_used = set(best_perm)
        assignment = []
        ctr = 0
        for n in np.arange(len(sub_df)):
            if n in peaks_used:
                assignment.append(ordered[ctr])
                ctr+=1
            else:
                assignment.append(None)
        sub_df['assignment'] = assignment
        losses = len(sub_df)*[loss]
        sub_df['loss'] = losses
        new_df = pd.concat([new_df,sub_df],ignore_index=True)
        if plot:
            fig, ax = plt.subplots()
            ax.plot(event_dt)
            counter=0
            ax.set_title(event + f" {loss}")
            for i in best_perm:
                val = sub_df.iloc[i]["peak_start"]
                ax.text(val,event_dt[val],best_icomb[counter])
                counter += 1
            plt.show()
dirname = os.path.dirname(df_loc)
file_text = os.path.splitext(os.path.basename(df_loc))[0]
new_file_path = os.path.join(dirname, f"peak_assignments_for_{file_text}.pkl")
new_df.to_pickle(new_file_path)
        