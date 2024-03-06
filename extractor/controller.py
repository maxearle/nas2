from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QTimer
from view import ErrorDialog, AllDone
from model import EventError, ReachedEnd, BadIndex
import os
import logging
import matplotlib.pyplot as plt
import numpy as np
from math import ceil
from utils.util_funcs import check_path_existence, is_nan_ignore_None, dir_contains_ext
from view import MainWindow
from model import Model
import glob

class Controller():
    """This class is the home of all the spaghetti in this program. It ties together the view part of the program(GUI) and the underlying
    model (the data processing). It's not perfect in places, would be more readable if some changes to the UI and model were refactored as methods of the
    MainWindow and Model classes rather than implementing them here."""
    def __init__(self, view: MainWindow, model: Model):
        self._v = view
        self._m = model
        self.accepted_count = 0 #Tracks events accepted so far
        self.current_trace_n = 0 #Tracks batches of samples seen so far
        self.n_trace = 0 #Total number of traces to be looked at
        self.accepted_events = 0
        self.rejected_events = 0
        self._get_default_settings()
        self.settings_dict = self._v.get_all_settings()
        self.accept_timer = QTimer(self._v, interval = int(self.settings_dict["loop_delay"]), timeout = self.accept_event)
        self.reject_timer = QTimer(self._v, interval = int(self.settings_dict["loop_delay"]), timeout = self.reject_event)
        self._connect_IO_buttons()
        self._connect_start_button()

    #INITIALISATION FUNCTIONS THAT RUN SUCCESSFULLY ONLY ONCE
        
    def _get_default_settings(self):
        cfg_filename = os.path.join(os.getcwd(),"cfg.txt")
        with open(cfg_filename) as f:
            for line in f:
                if line[0] == "#":
                    continue
                no_space = "".join(line.split())
                split = no_space.split('=')
                if len(split) > 2:
                    ErrorDialog("cfg file should have only one setting per line!")
                    self._v.close()
                try:
                    self._v.settings_dict[split[0]].set_val(split[1])
                except:
                    ErrorDialog(f"Issue setting {split[0]} to {split[1]}; check setting name is correct (should be one of {self._v.settings_dict.keys()}).")
                    self._v.close()

    def _connect_IO_buttons(self):
        self._v.browseButton.clicked.connect(self.open_dir_dialog)

    def _initialise_data_and_display(self):
        #Checking path/file validity
        data_location = self._v.inputLineEdit.text()
        if not check_path_existence(data_location):
            ErrorDialog("Selected data path does not exist!")
            return None
        if not dir_contains_ext(data_location,'tdms'):
            ErrorDialog("Selected directory contains no .tdms files.")
            return None
        self.dir_path = data_location
        self._m.open_tdms_dir(self.dir_path)
        self._m.make_output_file(os.path.join(self.dir_path, 'EVENTS.hdf5'))
        self._m.add_group('current_data', attrs = {"sample_rate":self.settings_dict["sample_rate"].get_val()})

        #TODO REACHED HERE

        self._v.plots.set_l_label(f"Trace Plot: {self.current_trace_n}/{len(self._m.tdms)}")
        self.process_next()
        self.update_trace_plot()
        self.next_event()

    def _start_process(self):
        """Checks given paths are valid and connects the rest of the buttons"""
        if self._m.check_path_existence(self._v.io.get_input_dir()) and self._m.check_path_existence(os.path.dirname(self._v.io.get_output_path())):
            logging.info("Valid input directory provided")
            self._v.io.lock()
            self._v.cfg.buttons["Start"].setEnabled(False)
            self._initialise_data_and_display()
            self._connect_cfg_buttons()
        else:
            ErrorDialog("Invalid directory or output path entered; please select a valid directory and try again.")

    
    def _connect_start_button(self):
        """Start button is connected first, before the rest which are only connected if valid filepaths are given"""
        self._v.cfg.buttons["Start"].clicked.connect(self._start_process)

        
    def _connect_cfg_buttons(self):
        self._v.cfg.buttons["Next batch"].clicked.connect(self.next_valid_batch)
        self._v.cfg.buttons["Accept event"].clicked.connect(self.accept_event)
        self._v.cfg.buttons["Reject event"].clicked.connect(self.reject_event)
        self._v.cfg.buttons["Keep accepting"].clicked.connect(self.start_accepting)
        self._v.cfg.buttons["Keep rejecting"].clicked.connect(self.start_rejecting)
        self._v.cfg.buttons["Pause"].clicked.connect(self.pause)
        self._v.cfg.buttons["Finish"].clicked.connect(self.finish)

    #DATA PROCESSING FUNCTIONS THAT UPDATE MODEL STATE

    def next_valid_batch(self):
        self.process_next()
        self.update_trace_plot()
        self.update_l_label()
        self.next_event()

    def next_event(self):
        """Loads next event from batch into model memory, if there are none/ no more moves onto next valid batch which calls this function again."""
        try:
            self._m.next_event(int(self._v.cfg["Event Berth"]))
            self.update_event_plot()
            self.update_r_label()

            for pos in self._m.event_boundaries[int(self._m.current_event_index)]:
                self._v.plots.l_vline(pos/int(self._v.cfg["Sample Rate"]), c='r')

        except EventError:
            logging.info("Event index is NaN, moving to next batch.")
            self.next_valid_batch()

    def process_next(self):
        """Processes the next batch of data and handles any rejections on account of missing events or high range etc.
        the program will stay in this loop until a valid batch is found."""
        while True:
            try:
                self._m.next_file()
            except ReachedEnd:
                self.finish()
            self.current_trace_n += 1
            if self._v.cfg["Correct trace slope"]:
                logging.info("Correcting trace slope")
                try:
                    self._m.slope_fix_average_run_method(self._m.current_data)
                except:
                    print(f"Failed on file {self._m.tdms.get_file_name()}")
            self._m.update_event_boundaries(float(self._v.cfg["Event Threshold"]), int(self._v.cfg["Gap tolerance"]))
            if len(self._m.event_boundaries) == 0:
                logging.info("No events in batch, moving on...")
                continue
            break
        logging.debug(f"{len(self._m.current_data)} samples loaded.")

    #EVENT HANDLING FUNCTIONS

    def accept_event(self):
        """Creates new dataset for event on plot and moves onto next"""
        logging.info("Creating new dataset for accepted event.")
        self.accepted_count += 1
        berth = int(self._v.cfg["Event Berth"])
        sample_rate = int(self._v.cfg["Sample Rate"])
        ename = f"Event_No_{self.accepted_count}"
        event_attrs = self._m.gen_event_attrs(ename,berth, sample_rate)
        self._m.create_dataset(self.grp_name,ename,self._m.event_data)
        self._m.add_to_df(event_attrs)
        self.accepted_events += 1
        self.next_event()

    def reject_event(self):
        logging.info("Rejecting event.")
        self.rejected_events += 1
        self.next_event()

    #EVENT HANDLING LOOP FUNCTIONS

    def start_accepting(self):
        """Starts timer to accept every event after user-defined pause"""
        self.accept_timer = QTimer(self._v, interval = int(self._v.cfg["Loop delay"]), timeout = self.accept_event)
        self.accept_timer.start()
        self.update_r_label()
        for name, button in self._v.cfg.buttons.items():
            if name == "Pause":
                continue
            button.setEnabled(False)
            
    
    def start_rejecting(self):
        """Starts timer to reject every event after user-defined pause"""
        self.reject_timer = QTimer(self._v, interval = int(self._v.cfg["Loop delay"]), timeout = self.reject_event)
        self.reject_timer.start()
        self.update_r_label()
        for name, button in self._v.cfg.buttons.items():
            if name == "Pause":
                continue
            button.setEnabled(False)

    def pause(self):
        logging.info("Pause signal sent")
        logging.debug(f"Accept loop: {self.accept_timer.isActive()}, Reject loop: {self.reject_timer.isActive()}")
        if self.accept_timer.isActive():
            self.accept_timer.stop()
        if self.reject_timer.isActive():
            self.reject_timer.stop()
        logging.debug(f"After pause; Accept loop: {self.accept_timer.isActive()}, Reject loop: {self.reject_timer.isActive()}")
        self.update_r_label()
        for name, button in self._v.cfg.buttons.items():
            button.setEnabled(True)

    #GUI STUFF

    def open_dir_dialog(self):
        dir_name = QFileDialog.getExistingDirectory(self._v, 'Select Directory Containing Input Files')
        self._v.io.set_input_dir(dir_name)

    def open_file_dialog(self):
        dir_name = QFileDialog.getExistingDirectory(self._v, 'Select Directory for Output File')
        self._v.io.set_output_path(os.path.join(dir_name, "EVENTS.hdf5"))
    
    def update_trace_plot(self):
        """Updates left plot with trace and generates real-time axis"""
        t = self._m.gen_timescale(self._m.current_data, int(self._v.cfg["Sample Rate"]))
        self._v.plots.l_clear_and_plot(self._m.current_data, t)

    def update_event_plot(self):
        """Similar to above method for the trace plot"""
        t = self._m.gen_timescale(self._m.event_data, int(self._v.cfg["Sample Rate"]))
        self._v.plots.r_clear_and_plot(self._m.event_data, t)

    def update_l_label(self):
        self._v.plots.set_l_label(f"Trace Plot: {self.current_trace_n}/{len(self._m.tdms)} \n {self._m.tdms.get_file_name()}")

    def update_r_label(self):
        """Updates right plot label with current event number / events in batch as well as the current status of the accept/reject loops.
        Later may implement counter of number of events seen, reject, accepted."""
        if self.accept_timer.isActive():
            self._v.plots.set_r_label(f"Event Plot: {self._m.current_event_index + 1}/{len(self._m.event_boundaries)}; A: {self.accepted_events}, R: {self.rejected_events}; Accepting...")
        if self.reject_timer.isActive():
            self._v.plots.set_r_label(f"Event Plot: {self._m.current_event_index + 1}/{len(self._m.event_boundaries)}; A: {self.accepted_events}, R: {self.rejected_events}; Rejecting...")
        self._v.plots.set_r_label(f"Event Plot: {self._m.current_event_index + 1}/{len(self._m.event_boundaries)}; A: {self.accepted_events}, R: {self.rejected_events}")

    #CLEANUP

    def finish(self):
        """Closes output file and the window"""
        self._v.close()
        out_dir = os.path.dirname(self._v.io.get_output_path())
        self._m.output_df.to_pickle(os.path.join(out_dir, "props.pkl"))
        AllDone(f"All done! {len(self._m.tdms.file_list)} tdms files read, {self.accepted_count} events saved.")