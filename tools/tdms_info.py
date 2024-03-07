"""
Use this script to analyse a TDMS file for diagnostic purposes.
"""

import nptdms as nt

filename = r"E:\For Max March 4 2024\With Urea\11111timecourse-Jan30-2024\Separateevent     1.tdms"

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