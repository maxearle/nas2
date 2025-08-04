from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QTimer
from view import ErrorDialog, AllDone
from model import EventError, ReachedEnd, BadIndex
import os
import logging
import matplotlib.pyplot as plt
import numpy as np
from math import ceil
from extractor_utils.util_funcs import check_path_existence, is_nan_ignore_None, dir_contains_ext, writeline_in
from view import MainWindow
from model import Model
import glob
import datetime
import sys

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
        self.plotting = True
        self._set_initial_state()
        self._get_default_settings()
        try:
            self.settings_dict = self._v.get_all_settings()
        except TypeError:
            ErrorDialog("Some default setting/s are of the wrong type. Correct this and try again.")
            self._v.close()
            return None
        self._initialise_logger()
        self.accept_timer = QTimer(self._v, interval = int(self.settings_dict["loop_delay"]), timeout = self.accept_event)
        self.reject_timer = QTimer(self._v, interval = int(self.settings_dict["loop_delay"]), timeout = self.reject_event)
        self._connect_buttons()

    #INITIALISATION FUNCTIONS THAT RUN SUCCESSFULLY ONLY ONCE
        
    def _initialise_logger(self):
        logging.getLogger().addHandler(self._v.logger)
        logging.getLogger().setLevel(logging.INFO)
        
    def _create_dump_file(self):
        self.dump_path = os.path.join(self.dir_path,"dump.txt")
        if check_path_existence(self.dump_path):
            logging.info("Dump file already exists. Replacing with new one.")
            os.remove(self.dump_path)
        
    def _set_initial_state(self):
        self._v.lock_all_controls()

    def _get_default_settings(self):
        __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))
        cfg_filename = os.path.join(__location__, 'cfg.txt')
        with open(cfg_filename) as f:
            for line in f:
                if line[0] == "#":
                    continue
                no_space = "".join(line.split())
                split = no_space.split('=')
                if len(split) > 2:
                    ErrorDialog("cfg file should have only one setting per line!")
                    self._v.close()
                    return None
                try:
                    self._v.settings_dict[split[0]].set_val(split[1])
                except:
                    ErrorDialog(f"Issue setting {split[0]} to {split[1]}; check setting name is correct (should be one of {self._v.settings_dict.keys()}).")
                    self._v.close()
                    return None

    def _connect_IO_buttons(self):
        self._v.browseButton.clicked.connect(self.open_dir_dialog)

    def _connect_buttons(self):
        self._v.browseButton.clicked.connect(self.open_dir_dialog)
        self._v.startButton.clicked.connect(self._initialise_data_and_display)
        self._v.skipButton.clicked.connect(self.next_valid_batch)
        self._v.acceptButton.clicked.connect(self.accept_event)
        self._v.rejectButton.clicked.connect(self.reject_event)
        self._v.keepAcceptingButton.clicked.connect(self.start_accepting)
        self._v.keepRejectingButton.clicked.connect(self.start_rejecting)
        self._v.pauseButton.clicked.connect(self.pause)
        self._v.finishButton.clicked.connect(self.finish)
        self._v.turboMode.clicked.connect(self.turbo_switch)

    def _initialise_data_and_display(self):
        #Checking path/file validity
        data_location = self._v.inputLineEdit.text()
        if not check_path_existence(data_location):
            ErrorDialog("Selected data path does not exist!")
            return None
        if not dir_contains_ext(data_location,'tdms'):
            ErrorDialog("Selected directory contains no .tdms files.")
            return None
        logging.info(f"Valid directory provided: {data_location}")
        try:
            self.settings_dict = self._v.get_all_settings()
        except:
            ErrorDialog("Incorrect settings. Please correct and try again.")
            return None
        self.dir_path = data_location
        self._create_dump_file()
        self._m.open_tdms_dir(self.dir_path)
        self._m.make_output_file(os.path.join(self.dir_path, 'EVENTS.hdf5'))
        self._m.add_group('current_data', attrs = {"sample_rate":self.settings_dict["sample_rate"]})

        self._v.tracePlot.set_title(f"Trace Plot: {self.current_trace_n}/{len(self._m.tdms)}")
        self._v.lock_IO_panel()
        self._v.unlock_all_controls()
        self._v.lock_start_settings()

        self.process_next()
        self.update_trace_plot()
        self.next_event()
 
    #DATA PROCESSING FUNCTIONS THAT UPDATE MODEL STATE

    def next_valid_batch(self):
        self.process_next()
        self.update_trace_plot()
        self.update_l_label()
        self.next_event()

    def next_event(self):
        """Loads next event from batch into model memory, if there are none/ no more moves onto next valid batch which calls this function again."""
        try:
            self._m.next_event(int(self.settings_dict['event_berth']))
            self.update_event_plot()
            self.update_r_label()
            if self.plotting:
                for pos in self._m.event_boundaries[int(self._m.current_event_index)]:
                    self._v.tracePlot.plot_vline(pos/int(self.settings_dict['sample_rate']), c='r')

        except EventError:
            logging.info(f"Finished file '{self._m.tdms.file_list[self._m.tdms.current_file]}'")
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
            logging.debug("Correcting trace slope")
            try:
                self._m.slope_fix_average_run_method(self._m.current_data)
            except:
                logging.info(f"Slope correction and therefore extraction failed on file {self._m.tdms.get_file_name()}. Skipping.")
                writeline_in(self.dump_path,f"{datetime.datetime.now()}: Couldn't correct slope or extract events in {self._m.tdms.get_file_name()}")
                continue
            self._m.update_event_boundaries(float(self.settings_dict['event_thresh']), int(self.settings_dict["gap_tol"]))
            if len(self._m.event_boundaries) == 0:
                logging.debug(f"No events in file {self._m.tdms.get_file_name()}, moving on...")
                writeline_in(self.dump_path,f"{datetime.datetime.now()}: Found no events in {self._m.tdms.get_file_name()}.")
                continue
            break
        logging.debug(f"{len(self._m.current_data)} samples loaded.")

    #EVENT HANDLING FUNCTIONS

    def accept_event(self):
        """Creates new dataset for event on plot and moves onto next"""
        logging.debug("Creating new dataset for accepted event.")
        self.accepted_count += 1
        berth = int(self.settings_dict["event_berth"])
        sample_rate = int(self.settings_dict["sample_rate"])
        ename = f"Event_No_{self.accepted_count}"
        event_attrs = self._m.gen_event_attrs(ename,berth, sample_rate)
        self._m.create_dataset('current_data',ename,self._m.event_data)
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
        self.accept_timer = QTimer(self._v, interval = int(self.settings_dict['loop_delay']), timeout = self.accept_event)
        self.accept_timer.start()
        self.update_r_label()
        self._v.lock_controls_loop()
            
    
    def start_rejecting(self):
        """Starts timer to reject every event after user-defined pause"""
        self.reject_timer = QTimer(self._v, interval = int(self._v.cfg["Loop delay"]), timeout = self.reject_event)
        self.reject_timer.start()
        self.update_r_label()
        self._v.lock_controls_loop()

    def pause(self):
        logging.info("Pause signal sent")
        logging.debug(f"Accept loop: {self.accept_timer.isActive()}, Reject loop: {self.reject_timer.isActive()}")
        if self.accept_timer.isActive():
            self.accept_timer.stop()
        if self.reject_timer.isActive():
            self.reject_timer.stop()
        logging.debug(f"After pause; Accept loop: {self.accept_timer.isActive()}, Reject loop: {self.reject_timer.isActive()}")
        self.update_r_label()
        self._v.unlock_controls_loop()

    #GUI STUFF

    def open_dir_dialog(self):
        dir_name = QFileDialog.getExistingDirectory(self._v, 'Select Directory Containing Input Files')
        self._v.inputLineEdit.setText(dir_name)

    def turbo_switch(self):
        """Bit hacky... maybe refine later."""
        self.plotting = not self.plotting
        if not self.plotting:
            self._v.tracePlot.clear_axes()
            self._v.tracePlot.text("YOU ARE IN TURBO MODE, \n THERE WILL BE NO PLOTTING TODAY", c='r')
            self._v.tracePlot.update_toolbar()
            self.update_l_label()
            self._v.eventPlot.clear_axes()
            self._v.eventPlot.text("YOU ARE IN TURBO MODE, \n THERE WILL BE NO PLOTTING TODAY",c='r')
            self._v.eventPlot.update_toolbar()

        if self.plotting:
            self.update_event_plot()
            self.update_r_label()
            self.update_trace_plot()
            self.update_l_label()
    
    def update_trace_plot(self):
        """Updates left plot with trace and generates real-time axis"""
        if self.plotting:
            self._v.tracePlot.clear_axes()
            self._v.tracePlot.label_x("Time /s")
            self._v.tracePlot.label_y("Current /nA")

            self._v.tracePlot.plot(np.arange(len(self._m.current_data))/self.settings_dict['sample_rate'], self._m.current_data)
            self._v.tracePlot.update_toolbar()
        else:
            logging.debug("No trace plot produced due to turbo mode.")

    def update_event_plot(self):
        """Similar to above method for the trace plot"""
        if self.plotting:
            self._v.eventPlot.clear_axes()
            self._v.eventPlot.label_x("Time /s")
            self._v.eventPlot.label_y("Current /nA")

            self._v.eventPlot.plot((np.arange(len(self._m.event_data))-self.settings_dict['event_berth'])/self.settings_dict['sample_rate'], self._m.event_data)
            self._v.eventPlot.update_toolbar()
        else:
            logging.debug("No event plot produced due to turbo mode.")

    def update_l_label(self):
        self._v.tracePlot.set_title(f"Trace: {self.current_trace_n}/{len(self._m.tdms)}, baseline noise {self._m.noise} \n {self._m.tdms.get_file_name()}")

    def update_r_label(self):
        """Updates right plot label with current event number / events in batch as well as the current status of the accept/reject loops.
        Later may implement counter of number of events seen, reject, accepted."""
        if self.plotting:
            if self.accept_timer.isActive():
                self._v.eventPlot.set_title(f"Event Plot: {self._m.current_event_index + 1}/{len(self._m.event_boundaries)}; A: {self.accepted_events}, R: {self.rejected_events}; Accepting...")
            if self.reject_timer.isActive():
                self._v.eventPlot.set_title(f"Event Plot: {self._m.current_event_index + 1}/{len(self._m.event_boundaries)}; A: {self.accepted_events}, R: {self.rejected_events}; Rejecting...")
            self._v.eventPlot.set_title(f"Event Plot: {self._m.current_event_index + 1}/{len(self._m.event_boundaries)}; A: {self.accepted_events}, R: {self.rejected_events}")

    #CLEANUP

    def finish(self):
        """Closes output file and the window"""
        self._v.close()
        self._m.output_df.to_pickle(os.path.join(self.dir_path, "props.pkl"))
        self._m.output.close()
        AllDone(f"All done! {len(self._m.tdms.file_list)} tdms files read, {self.accepted_count} events saved.")
        sys.exit()
        