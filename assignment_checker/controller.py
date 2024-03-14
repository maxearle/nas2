from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import Qt
from model import Model, check_path_existence, get_file_ext, parse_pois, straight_line, check_binary
from view import MainWindow, ErrorDialog
import numpy as np
import logging
import matplotlib as mpl
from matplotlib.pyplot import cm
import os

def open_file_dialog(filt: str):
    qfd = QFileDialog()
    path = None
    f = qfd.getOpenFileName(qfd, "Select File", path, filt)
    return f[0]

class Controller():
    def __init__(self, version = 'Default'):
        self.version = version
        self.model = Model()
        self.view = MainWindow(self.version)

        self._initialise_buttons()

    def _initialise_buttons(self):
        #State
        self.view.enable_io()
        self.view.disable_all_controls()
        #Connections
        self.view.chooseDataButton.clicked.connect(self.select_data)
        self.view.chooseDfButton.clicked.connect(self.select_df)
        self.view.startButton.clicked.connect(self.start)
        self.view.prevButton.clicked.connect(self.prev_event)
        self.view.nextButton.clicked.connect(self.next_event)
        self.view.acceptButton.clicked.connect(self.accept_df_assignment)
        self.view.rejectButton.clicked.connect(self.reject_event)
        self.view.rejectButton.clicked.connect(self.save)
        self.view.enterButton.clicked.connect(self.enter_alt_assignment)
        self.view.clicked.connect(self.clear_focus)
        self.view.closed.connect(self.close_h5)
        #Keypresses
        self.view.keyPressed.connect(self.key_press_handler)

    def key_press_handler(self,key):
        if key == Qt.Key.Key_Return:
            self.enter_alt_assignment()
        elif key == Qt.Key.Key_Period:
            self.next_event()
        elif key == Qt.Key.Key_Comma:
            self.prev_event()
        elif key == Qt.Key.Key_R:
            self.reject_event()
        elif key == Qt.Key.Key_A:
            self.accept_df_assignment()
        elif key == Qt.Key.Key_S:
            self.save()
        elif key == Qt.Key.Key_0:
            if not (self.view.focusWidget() == self.view.altAssEntry):
                self.view.altAssEntry.setFocus()
                self.view.altAssEntry.insert("0")
        elif key == Qt.Key.Key_1:
            if not (self.view.focusWidget() == self.view.altAssEntry):
                self.view.altAssEntry.setFocus()
                self.view.altAssEntry.insert("1")



    def close_h5(self):
        self.model.close()
        logging.info("HDF5 File closed.")

    def select_data(self):
        path = open_file_dialog('HDF5 (*.hdf5)')
        logging.info(f"{path} selected as data source.")
        self.view.dataLocation.setText(path)

    def select_df(self):
        path = open_file_dialog('PKL File (*.pkl)')
        logging.info(f"{path} selected as dataframe.")
        self.view.dataframeLocation.setText(path)

    def start(self):
        #Checking path/file validity, opening files and adding to model
        self.data_location = self.view.dataLocation.text()
        self.dataframe_location = self.view.dataframeLocation.text()
        if not check_path_existence(self.data_location):
            ErrorDialog("Selected data path does not exist!")
            return None
        if not get_file_ext(self.data_location) == '.hdf5':
            ErrorDialog("Selected file does not have extension '.hdf5'.")
            return None
        self.model.import_data(self.data_location)
        if self.dataframe_location != "":
            if not check_path_existence(self.dataframe_location):
                ErrorDialog("Selected dataframe path does not exist!")
                return None
            if not get_file_ext(self.dataframe_location) == '.pkl':
                ErrorDialog("Selected file does not have extension '.pkl'.")
                return None
            self.model.import_df(self.dataframe_location)
        else:
            self.model.df = None

        try:
            self.model.pois = parse_pois(self.view.poiList.text())
        except:
            ErrorDialog("Couldn't parse POIs list; try again!")
            return None

        #Locking all IO fields and buttons
        self.view.disable_io()
        #Unlocking Controls
        self.view.enable_all_controls()
        #Initialising assignments dataframe
        self.model._create_assignments_df()
        #Load first event and plot
        self.model.hData.next_ds()
        self.plot_event()

    def plot_event(self):
        #Reset
        self.view.eventPlot.clear_axes()
        #Get data and plot
        data = self.model.hData.get_current_data()[:]
        x_data = np.arange(len(data))
        self.view.eventPlot.plot(x_data,data)

        if self.model.df is not None:
            name = self.model.hData.get_current_name()
            logging.info(f"Selecting suggested assignments for {name}.")
            subDf = self.model.query_df(f"name == '{name}'")
            assigned_peaks_df = subDf[subDf['assignment'].notnull()]
            colours = iter(cm.rainbow(np.linspace(0,1,len(assigned_peaks_df))))
            for i, assigned_peak in assigned_peaks_df.iterrows():
                c = next(colours)
                pl, pr = assigned_peak['peak_start'], assigned_peak['peak_end']
                baseline_grad = -(data[pl]-data[pr])/(pr-pl)
                baseline_int = data[pl]-baseline_grad * pl
                peak_baseline = straight_line(np.arange(pl,pr+1),baseline_grad,baseline_int)
                peak_data = data[pl:pr + 1]
                self.view.eventPlot.fill_between(np.arange(pl,pr+1),peak_data,peak_baseline,fc=c)
                self.view.eventPlot.text(pl + 0.05,data[pl],assigned_peak['assignment'],c=c)
            inv_map = {v: k for k, v in self.model.pois.items()}
            print(inv_map)
            self.view.eventPlot.set_title(f"{self.model.hData.get_current_name()}, {self.model.hData.current_ds_index + 1} / {len(self.model.hData)}, {[inv_map[int(i)] for i in set(self.model.pois.values()).intersection(set(assigned_peaks_df['assignment']))]} POIs present, Loss: {np.mean(subDf['loss'])}")
        else:
            self.view.eventPlot.set_title(f"{self.model.hData.get_current_name()}, {self.model.hData.current_ds_index + 1} / {len(self.model.hData)}")

        self.view.eventPlot.label_y("Current /nA")
        self.view.eventPlot.update_toolbar()

    def next_event(self):
        self.model.hData.next_ds()
        self.plot_event()

    def prev_event(self):
        self.model.hData.prev_ds()
        self.plot_event()

    def enter_alt_assignment(self):
        toparse = self.view.altAssEntry.text()
        if (len(toparse) == len(self.model.pois)) & check_binary(toparse):
            pois_present = [int(n) == 1 for n in list(toparse)]
            new_ass = {list(self.model.pois.keys())[i]:pois_present[i] for i in np.arange(len(self.model.pois))}
            self.model.change_assignments(self.model.hData.current_ds_index, new_ass)
            logging.info(f"Assigned {self.model.hData.get_current_name()} with {new_ass}.")
            self.view.altAssEntry.clear()
            self.view.altAssEntry.clearFocus()
            self.next_event()
        else:
            ErrorDialog("Couldn't parse alternative assignment: check it's the right length and contains only 1s and 0s.")

    def accept_df_assignment(self):
        if self.model.df is not None:
            subDf = self.model.query_df(f"name == '{self.model.hData.get_current_name()}'")
            assigned_peaks_df = subDf[subDf['assignment'].notnull()]
            assigned_set = set([int(list(assigned_peaks_df['assignment'])[i]) for i in np.arange(len(assigned_peaks_df))])
            pois_present = assigned_set.intersection(set(self.model.pois.values()))
            inv_map = {v: k for k, v in self.model.pois.items()}
            new_ass = {list(self.model.pois.keys())[i]:(self.model.pois[list(self.model.pois.keys())[i]] in pois_present) for i in np.arange(len(self.model.pois))}
            self.model.change_assignments(self.model.hData.current_ds_index, new_ass)
            logging.info(f"Assigned {self.model.hData.get_current_name()} with {new_ass}.")
            self.next_event()
        else:
            ErrorDialog("There is no assignments dataframe provided to accept suggestions from!")

    def reject_event(self):
        new_ass = {list(self.model.pois.keys())[i]:None for i in np.arange(len(self.model.pois))}
        self.model.change_assignments(self.model.hData.current_ds_index, new_ass)
        self.model.hData.next_ds()
        self.plot_event()

    def clear_focus(self):
        if self.view.focusWidget() is not None:
            self.view.focusWidget().clearFocus()

    def save(self):
        dirname = os.path.dirname(self.dataframe_location)
        file_text = os.path.splitext(os.path.basename(self.dataframe_location))[0]
        self.model.assignments.to_pickle(os.path.join(dirname, f"checked_assignments_from_{file_text}.pkl"))
        logging.info(f"Saved assignments to {os.path.join(dirname, f'checked_assignments_from_{file_text}.pkl')}")