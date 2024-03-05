"""Use this script to analyse a TDMS file for diagnostic purposes."""

import nptdms as nt

filename = r"E:\Raluca29Feb24\0.0025TWEEN_300pmsample4.3\2600_24-02-29_1400_018.tdms"

dt = nt.TdmsFile.read(filename)
grps = dt.groups()
print(f"This file contains the groups: {grps}")
for grp in grps:
    chans = grp.channels()
    print(f"Group {grp} contains the following channels/properties:")
    print("::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
    for chan in chans:
        print(chan)
        print(chan.properties)
        print(chan[:])
        print(f"{len(chan)} samples")
        print("*************************************************************************")