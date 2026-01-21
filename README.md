# Nanopore Analysis Suite 2 (nas2)
This is the second version of the nas (Nanopore Analysis Suite) collection of Python software for analysing tdms files containing nanopore impedance sensing data. It was developed by Max K. Earle whilst working towards his PhD at the University of Cambridge supervised by Prof. Ulrich Keyser, and was written to facilitate the analysis of data from nanopore impedance sensing at KeyserLab. The extractor software was made significantly more robust for data from busy samples in order to allow the analysis of total RNA ([Patiño-Guillén, G., Pešović, J., Panić, M., Earle, M., Ninković, A., Petruşca, S., ... & Bošković, F. (2025). Quantification of disease-associated RNA tandem repeats by nanopore sensing. bioRxiv, 2025-05.](https://www.biorxiv.org/content/10.1101/2025.05.15.653973v1.abstract))

Development of this repository is not currently active, as I've started a new job as a postdoctoral research associate at Imperial College London. If you are interested in contributing or taking over development, please send a message to mearle@imperial.ac.uk.

## Installation
Installation is best done in a new Python virtual environment in Python version 3.12.2. Using `pyvenv`, this can be done by navigating to the desired root directory in a terminal and executing:

`py -m venv nas2`

Then either clone this repo or download and copy its files to the relevant venv directory created.

Activate the newly-created virtual environment and install the dependencies list from the file "requirements.txt", for example using:

`pip install -r requirements.txt`

Installation of Qt6 may also be required for the software to run. Get Qt6 [here](https://doc.qt.io/qt-6/get-and-install-qt.html).
## Usage
Each piece of software in `nas2` (`extractor`, `multi_filter`, `assigner`) is intended to be used independently as a GUI-based program. Each represents part of a rough pipeline (of which all parts may not be necessary for your application).

`extractor` is used to extract independent nanopore translocation events from raw data in a "tdms" file and store them in a newly-created "EVENTS.hdf5". An example tdms file for testing is included in this repository: `example_trace.tdms`.

Launch `extractor` by running the `extractor.py` file in its directory with the `nas2` virtual environment active. Enter the information about your data and the desired extractor settings in the panel on the bottom left. The adjustable settings are:
- The measurement sample rate in Hz (to scale events in time correctly)
- The event threshold in nA (the minimum current level relative to the baseline that should mark an "event")
- The event berth (the number of samples each side that should be included in the extracted events' data)
- The gap tolerance (the number of consecutive samples below the set event threshold that are tolerated within a single event, preventing transient current noise from splitting events in two).

Click "Browse" and choose the root directory containing the tdms files to be analysed. Then, click "Validate choice and start". This will start the analysis and lock the extractor settings panel on the bottom left. The canvas on the left should show the first raw data trace from the measurement. Vertical red lines will indicate the first detected event, whose trace will be shown in the panel on the right. Control of the software including accepting and rejecting events is controlled from the "controls" panel on the bottom right. Click "Accept Event" and "Reject Event" to accept and reject events one at a time and move onto the next. If you are happy with the settings and just want to extract every event, click "Keep Accepting". In "Keep Accepting" mode the software will aim to accept events once per the amount of time in the "Loop Delay field", but it can often run slower as it has to update the canvas every time. To speed this up for large datasets, it's recommend to turn on Turbo Mode with the "Toggle Turbo Mode" button to turn off plotting and run autonomously. If one of the tdms files is problematic or clearly there has been a temporary issue with the measurement, click "Skip File" to skip to the next tdms file. Once the analysis is finished, or if the "Finish" button is pressed, the software will close and the extracted events will be saved in an EVENTS.hdf5 file. Event properties will also be saved in a pickled `pandas` `DataFrame` object to a file called "props.pkl" in the directory containing the tdms files.

The EVENTS.hdf5 file created contains a single group, `current_data`, with event current data saved as named datasets therein. The props.pkl dataframe contains the names of each event (identical to the corresponding dataset name in the EVENTS.hdf5) and various properties such as mean current, duration, e.c.d. (event charge deficit ~ area), the ffap (first fifth area percentage), the lfap (last fifth area percentage) and skew (=ffap/lfap).

Extracted events can be manually cleaned in an efficient way using the `multi_filter` tool. Launch the tool by running `multi_filter.py`. First choose the hdf5 file containing your extracted events and the pkl describing their properties using the "Choose data" and "Choose Input Dataframe" buttons at the top of the window. Then, click "Start". This will unlock the "Name column" dialogue, allowing you to choose the column of the properties dataframe containing event names. Click "Lock in Names" once satisfied. The software is then operated by choosing pairs of properties from the comboboxes in the bottom left panel and clicking "Update plot" to plot every event named in the pkl file against each other in a 2D scatter plot. This permits clusters of events with similar properties to be identified. Events can be identified by clicking on a point in the scatter plot, whose trace will then be shown in the panel on the right.

Filtering can be accomplished by drawing lines splitting the scatter plot or drawing a lasso selection around desired points using the buttons "Create Split Line Selection" or "Select points with Lasso" in the bottom control bar. Once points have been selected, these points can either be kept or removed from the scatter plot (masked or inverse masked) using the relevant buttons in the control bar. Kept events can be saved to a new dataframe using the labelled button in the bottom right. This will open a dialogue asking you to choose a name for the new dataframe. This allows you to save "checkpoints" in the filtering procedure to be re-visited. If you wish to analyse a new dataset, the program's state will be reset to the starting point if "New Dataset" in the top right is selected.

`Assigner` is a tool for assigning binary barcodes to events. This tool is more specialised and was written for another project hopefully to be published soon. When that happens, this will be updated with more usage instructions.
## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.
## License

[MIT](https://choosealicense.com/licenses/mit/)
