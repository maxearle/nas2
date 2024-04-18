from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import Qt
from model import Model, check_path_existence, get_file_ext, Point, get_line, straight_line, remove_bad_values, isbelow, diff_dfs, union_dfs
from view import MainWindow, ErrorDialog
import numpy as np
import logging
import matplotlib as mpl
from matplotlib.widgets import Lasso
from matplotlib import path
import pandas as pd

#TODO In this module there's a lot of logic (specifically pertaining to the selection of split points)
#that I feel should be moved to the Model. This would make resetting things easier, since currently they all have to be reset manually by assignment.
#Would be easier if you could just get a new instance of the Model which works to reset all the other logical stuff.

def open_file_dialog(filt: str):
    qfd = QFileDialog()
    path = None
    f = qfd.getOpenFileName(qfd, "Select File", path, filt)
    return f[0]

def save_dialog(root: str, ext: str):
    qfd = QFileDialog()
    path = None
    f = qfd.getSaveFileName(qfd, "Save Location", root, ext)
    return f[0]

class Controller():
    free_select: bool = False
    event_point = None
    split_point1: Point | None = None
    split_point1_artist = None
    split_point2: Point | None = None
    split_point2_artist = None
    split_line_artist = None
    shade_artist = None
    x_parameter: str | None
    y_parameter: str | None
    def __init__(self, version = "Default"):
        self.version = version
        self.model = Model()
        self.view = MainWindow(self.version)

        self.reset_view_state()
        self._initialise_buttons()

    #Initialisation

    def reset_model(self):
        self.model = Model()

    def reset_view_state(self):
        #Buttons that begin enabled
        self.view.chooseDataButton.setEnabled(True)
        self.view.chooseDfButton.setEnabled(True)
        self.view.startButton.setEnabled(True)
        self.view.dataLocation.setText("")
        self.view.dataLocation.setReadOnly(False)
        self.view.dataframeLocation.setText("")
        self.view.dataframeLocation.setReadOnly(False)
        self.view.saveSelectionButton.setEnabled(False)
        #Buttons that begin disabled
        self._switch_controls(False)
        self.view.lockNameButton.setEnabled(False)
        #Comboboxes that begin disabled
        self.view.xBox.clear()
        self.view.yBox.clear()
        self.view.nameBox.setEnabled(False)
        self.view.nameBox.clear()
        #Plots
        self.view.scatterPlot.clear_axes()
        self.view.eventPlot.clear_axes()
        #Reset variables
        self.event_point = None
        self.free_select = False
        self.split_point1 = None
        self.split_point2 = None
        self.split_point1_artist = None
        self.split_point2_artist = None
        self.split_line_artist = None
        self._reset_shading()
        self.x_parameter = None
        self.y_parameter = None
        

    def _initialise_buttons(self):
        self.view.startButton.clicked.connect(self.start)
        self.view.chooseDataButton.clicked.connect(self.select_data)
        self.view.chooseDfButton.clicked.connect(self.select_dataframe)
        self.view.newButton.clicked.connect(self.new)
        self.view.lockNameButton.clicked.connect(self.lock_names)
        self.view.updatePlotButton.clicked.connect(self.update_scatter_plot)
        self.scatter_cid = self.view.scatterPlot.canvas.mpl_connect('button_press_event', self.select_event)
        self.view.splitLineButton.clicked.connect(self.choose_first)
        self.view.lassoButton.clicked.connect(self.lasso_start)
        self.view.resetAllButton.clicked.connect(self.reset_selections)
        self.view.saveSelectionButton.clicked.connect(self.save_selection)
        self.view.deletePoints.clicked.connect(self.rm_selected_points)
        self.view.keepPoints.clicked.connect(self.rm_unselected_points)
        self.view.keyPressed.connect(self.key_press_control)

    def start(self):
        #Checking path/file validity
        data_location = self.view.dataLocation.text()
        dataframe_location = self.view.dataframeLocation.text()
        if not check_path_existence(data_location):
            ErrorDialog("Selected data path does not exist!")
            return None
        if not get_file_ext(data_location) == '.hdf5':
            ErrorDialog("Selected file does not have extension '.hdf5'.")
            return None
        if not check_path_existence(dataframe_location):
            ErrorDialog("Selected dataframe path does not exist!")
            return None
        if not get_file_ext(data_location) == '.hdf5':
            ErrorDialog("Selected file does not have extension '.pkl'.")
            return None
        
        #Opening files and adding to model
        self.model.open_hdf5(data_location)
        self.model.open_df(dataframe_location)

        #Locking all fields and other buttons except 'New Dataset'
        self.view.startButton.setEnabled(False)
        self.view.chooseDfButton.setEnabled(False)
        self.view.dataframeLocation.setReadOnly(True)
        self.view.chooseDataButton.setEnabled(False)
        self.view.dataLocation.setReadOnly(True)

        #Populating Name Column Selection Box
        cols = self.model.get_df_cols()
        self.view.nameBox.setEnabled(True)
        self.view.nameBox.addItems(cols)
        self.view.lockNameButton.setEnabled(True)

    def new(self):
        self.reset_model()
        self.reset_view_state()

    def select_data(self):
        path = open_file_dialog('HDF5 (*.hdf5)')
        logging.info(f"{path} selected as data source.")
        self.view.dataLocation.setText(path)

    def select_dataframe(self):
        path = open_file_dialog('PKL File (*.pkl)')
        logging.info(f"{path} selected as dataframe.")
        self.view.dataframeLocation.setText(path)
        
    def lock_names(self):
        index = self.view.nameBox.currentIndex()
        self.view.lockNameButton.setEnabled(False)
        self.view.nameBox.setEnabled(False)

        #Populate Control Comboboxes
        other_cols = self.model.get_df_cols(exclude = index)
        self.view.xBox.addItems(other_cols)
        self.view.xBox.setEnabled(True)
        self.view.yBox.addItems(other_cols)
        self.view.yBox.setEnabled(True)
        self.view.updatePlotButton.setEnabled(True)

    def update_scatter_plot(self):
        self._switch_controls(True)
        #Check selected parameters
        self.x_parameter = self.view.xBox.currentText()
        self.y_parameter = self.view.yBox.currentText()

        #Reset plots
        self.view.scatterPlot.clear_axes()
        self.view.eventPlot.clear_axes()

        #Reset Variables
        self.reset_splitline_params()
        self.event_point = None
        self._reset_shading()

        #Separate data into selected and unselected and plot in different colours
        all_x_data = np.array(self.model.df[self.x_parameter])
        all_y_data = np.array(self.model.df[self.y_parameter])
        logging.info(f"Plotting {len(self.model.df)} points...")
        if self.model.selection is not None:
            selected_x_data = np.array(self.model.selection[self.x_parameter])
            selected_y_data = np.array(self.model.selection[self.y_parameter])
            self.view.scatterPlot.scatter(selected_x_data,selected_y_data,alpha=0.1, c='r')
            unselected_df = diff_dfs(self.model.df,self.model.selection)
        else:
            unselected_df = self.model.df

        unsel_x_data = np.array(unselected_df[self.x_parameter])
        unsel_y_data = np.array(unselected_df[self.y_parameter])
        self.view.scatterPlot.scatter(unsel_x_data,unsel_y_data, alpha=0.1, c='b')
        logging.info("Done plotting.")

        #Set lims
        x_wo_bad_vals = remove_bad_values(all_x_data)
        x_range = np.ptp(x_wo_bad_vals)
        x_lims = (np.min(x_wo_bad_vals) - 0.05*x_range,np.max(x_wo_bad_vals) + 0.05*x_range)
        y_wo_bad_vals = remove_bad_values(all_y_data)
        y_range = np.ptp(y_wo_bad_vals)
        y_lims = (np.max(y_wo_bad_vals) + 0.05*y_range, np.min(y_wo_bad_vals) - 0.05*y_range)
        self.view.scatterPlot.set_lims(*y_lims, *x_lims)

        #Label axes
        self.view.scatterPlot.label_x(self.x_parameter)
        self.view.scatterPlot.label_y(self.y_parameter)

        #Update toolbar
        self.view.scatterPlot.update_toolbar()
        self.view.eventPlot.update_toolbar()

        #Reset plot titles
        self.view.scatterPlot.reset_title()
        self.view.eventPlot.reset_title()

        #Enable free select
        self.free_select = True

    def plot_event(self, name):
        event_data = self.model.get_event_data(name)
        t_data = np.arange(len(event_data))/self.model.get_sample_rate()

        self._clear_event_plot()

        self.view.eventPlot.plot(t_data, event_data)
        self.view.eventPlot.set_title(name)
        self.view.eventPlot.update_toolbar()

    def _clear_event_plot(self):
        self.view.eventPlot.clear_axes()
        self.view.eventPlot.label_x("Time /s")
        self.view.eventPlot.label_y("Current /nA")

    def plot_peak(self, name, peak_start, peak_end):
        event_data = self.model.get_event_data(name)
        pk_start = int(peak_start)
        pk_end = int(peak_end)
        sample_rate = self.model.get_sample_rate()
        t_data = np.arange(len(event_data))/sample_rate

        t_span = (pk_start/sample_rate,pk_end/sample_rate)
        baseline_grad = (event_data[pk_end]-event_data[pk_start])/(t_span[1]-t_span[0])
        baseline_int = event_data[pk_start]-baseline_grad * t_span[0]
        peak_baseline = straight_line(t_data[pk_start:pk_end+1],baseline_grad,baseline_int)
        peak_data = event_data[pk_start:pk_end + 1]
        self.view.eventPlot.fill_between(t_data[pk_start:pk_end+1],peak_data,peak_baseline,fc='r')

        self.view.eventPlot.update_toolbar()

    def select_event(self, event):
        #Miss all of this if app is not in free select mode
        if not self.free_select:
            return None
        

        logging.info(f"Click detected at {event.xdata}, {event.ydata} with free select on.")
        click = Point(event.xdata, event.ydata)

        #Picking nearest event (if there is one)
        picked = self.model.choose_event(click, (self.x_parameter, self.y_parameter))

        #Check whether any event was found
        if picked is None:
            logging.info("No valid events in vicinity of click.")
            self.model.current = None
            if self.event_point is not None:
                self.event_point.remove()
                self.event_point = None
                self.view.scatterPlot.update()
            self._clear_event_plot()
            self.view.eventPlot.update_toolbar()
            return None
        else:
            logging.info(f"Event named '{picked[self.view.nameBox.currentText()]}' selected, fetching data...")
            self.model.current = pd.DataFrame([picked])
            picked = picked.to_dict()

        #Plot event
        event_name = picked[self.view.nameBox.currentText()]
        self.plot_event(event_name)

        #If event has peak data, plot the peak too
        if "peak_start" in picked and "peak_end" in picked:
            self.plot_peak(event_name, picked["peak_start"],picked["peak_end"])

        #Remove any old points
        if self.event_point is not None:
            self.event_point.remove()
            self.event_point = None

        #Plot marker for selected event
        event_point = Point(picked[self.x_parameter], picked[self.y_parameter])
        self.event_point, = self.view.scatterPlot.plot_point(event_point, c='m', marker = 'o')

    def choose_first(self):
        #TODO this spaghetti could be later replaced with a context manager
        #Disable everything and disconnect free_select
        self.view.scatterPlot.canvas.mpl_disconnect(self.scatter_cid)
        self._switch_controls(False)

        self.scatter_cid = self.view.scatterPlot.canvas.mpl_connect('button_press_event',self._click_first)

        #Update axes title with instructions
        self.view.scatterPlot.set_title("Click first point on split line")

    def _click_first(self,event):
        self.split_point1 = Point(event.xdata, event.ydata)
        self._reset_shading()
        if self.split_line_artist is not None:
            self.split_line_artist.remove()
        if self.split_point1_artist is not None:
            self.split_point1_artist.remove()
        if self.split_point2_artist is not None:
            self.split_point2_artist.remove()
        self.split_point1_artist, = self.view.scatterPlot.plot_point(self.split_point1, c='g', marker = 'o')
        
        self._reset_shading()

        logging.info(f"Click detected at {event.xdata}, {event.ydata}, placing first point of split line.")


        #Disconnect split point selection callback, reconnect free select callback
        self.view.scatterPlot.canvas.mpl_disconnect(self.scatter_cid)
        self.scatter_cid = self.view.scatterPlot.canvas.mpl_connect('button_press_event', self._click_second)

        #Update axes title with instructions
        self.view.scatterPlot.set_title("Click second point on split line")

    def _click_second(self,event):
        self.split_point2 = Point(event.xdata, event.ydata)

        self.split_point2_artist, = self.view.scatterPlot.plot_point(self.split_point2, c='g', marker = 'o')

        logging.info(f"Click detected at {event.xdata}, {event.ydata}, placing second point of split line.")

        #Check to see if we can make a line now
        self.check_line()

        #Disconnect split point selection callback, reconnect free select callback
        self.view.scatterPlot.canvas.mpl_disconnect(self.scatter_cid)
        self.scatter_cid = self.view.scatterPlot.canvas.mpl_connect('button_press_event', self._click_region)

        #Update axes title with instructions
        self.view.scatterPlot.set_title("Click region containing desired selection")


    def check_line(self):
        if self.split_line_artist is not None:
            self.split_line_artist.remove()
        if self.split_point1 is not None and self.split_point2 is not None:
            logging.info("Two split points selected, trying to draw line...")
            x_data = np.array(self.model.df[self.x_parameter])
            x_range = np.linspace(np.nanmin(x_data),np.nanmax(x_data), 100)
            line_vars = get_line(self.split_point1, self.split_point2)
            self.split_line_artist, = self.view.scatterPlot.plot(x_range, straight_line(x_range, *line_vars), c = 'g')

    def _click_region(self, event):
        if self.split_line_artist is None:
            raise ValueError("Tried to select region whilst no split line was present.")
        self._reset_shading()
        
        self.model.region_point = Point(event.xdata,event.ydata)
        
        x_data = np.array(self.model.df[self.x_parameter])
        x_range = np.linspace(np.nanmin(x_data),np.nanmax(x_data), 100)

        y_data = np.array(self.model.df[self.y_parameter])

        line_vars = get_line(self.split_point1, self.split_point2)

        if isbelow(self.model.region_point, line_vars):
            self.shade_artist = self.view.scatterPlot.fill_between(x_range, np.nanmin(y_data), straight_line(x_range, *line_vars), alpha = 0.1, fc = 'g')
            logging.info(f"Click detected at {event.xdata}, {event.ydata}, shading below split line.")
        else:
            self.shade_artist = self.view.scatterPlot.fill_between(x_range, straight_line(x_range, *line_vars), np.nanmax(y_data), alpha = 0.1, fc = 'g')
            logging.info(f"Click detected at {event.xdata}, {event.ydata}, shading above split line.")

        #Connect enter press signal to slot for confirmation
        self.view.keyPressed.disconnect()
        self.view.keyPressed.connect(self.confirm)

        self.view.scatterPlot.set_title("Press 'Enter' to confirm selection")
            
    def confirm(self,key):
        if key == Qt.Key.Key_Return:
            line_vars = get_line(self.split_point1, self.split_point2)
            subDf = self.model.get_sub_df(self.model.region_point, (self.x_parameter, self.y_parameter), line_vars)
            self.reset_splitline_params()
            self._reset_shading()
            self.model.selection = subDf
            logging.info(f"Split selected {len(subDf)} points.")
            self.view.keyPressed.disconnect()
            self.view.keyPressed.connect(self.key_press_control)
            self.view.scatterPlot.canvas.mpl_disconnect(self.scatter_cid)
            self.scatter_cid = self.view.scatterPlot.canvas.mpl_connect('button_press_event',self.select_event)
            self._switch_controls(True)
            self.update_scatter_plot()

    def key_press_control(self,key):
        if key == Qt.Key.Key_D:
            self.rm_selected_points()
        elif key == Qt.Key.Key_K:
            self.rm_unselected_points()
        elif key == Qt.Key.Key_S:
            self.save_selection()

    def _reset_shading(self):
        if self.shade_artist is not None:
            self.shade_artist.remove()
            self.view.scatterPlot.update()
            self.shade_artist = None
            self.model.region_point = None
            self.view.saveSelectionButton.setEnabled(False)

    def _switch_controls(self,state: bool):
        self.view.splitLineButton.setEnabled(state)
        self.view.lassoButton.setEnabled(state)
        self.view.resetAllButton.setEnabled(state)
        self.view.saveSelectionButton.setEnabled(state)
        self.view.deletePoints.setEnabled(state)
        self.view.keepPoints.setEnabled(state)
        self.view.updatePlotButton.setEnabled(state)
        self.view.xBox.setEnabled(state)
        self.view.yBox.setEnabled(state)

    def reset_splitline_params(self):
        if self.split_point1_artist is not None:
            self.split_point1_artist.remove()
        if self.split_point2_artist is not None:
            self.split_point2_artist.remove()   
        if self.split_line_artist is not None:
            self.split_line_artist.remove()
        self._reset_shading()
        self.view.scatterPlot.update()
        self.view.eventPlot.update()
        self.split_point1 = None
        self.split_point2 = None
        self.split_point1_artist = None
        self.split_point2_artist = None
        self.split_line_artist = None

    def reset_selections(self):
        self.model.selection = None
        self.update_scatter_plot()


    def lasso_start(self):
        self.reset_selections()
        self._switch_controls(False)

        self.view.scatterPlot.canvas.mpl_disconnect(self.scatter_cid)
        self.scatter_cid = self.view.scatterPlot.canvas.mpl_connect('button_press_event', self._lasso)
        self.view.scatterPlot.set_title("Draw around selected points")

    def _lasso(self, event):
        self.lasso = Lasso(self.view.scatterPlot.canvas.axes, (event.xdata,event.ydata),self._lasso_selection)
        self.view.scatterPlot.canvas.mpl_disconnect(self.scatter_cid)
        self.scatter_cid = self.view.scatterPlot.canvas.mpl_connect('button_press_event', self.select_event)

    def rm_selected_points(self):
        full_selection = union_dfs(self.model.selection, self.model.current)
        self.model.df = diff_dfs(self.model.df,full_selection)
        self.model.selection=None
        self.model.current=None
        self.update_scatter_plot()

    def rm_unselected_points(self):
        full_selection = union_dfs(self.model.selection, self.model.current)
        self.model.df = full_selection
        self.model.selection=None
        self.model.current=None
        self.update_scatter_plot()

    def _lasso_selection(self, verts):
        try:
            x_data = np.array(self.model.df[self.x_parameter])
            y_data = np.array(self.model.df[self.y_parameter])
        except KeyError:
            logging.info(f"Failed to fetch data for parameters {self.x_parameter}, {self.y_parameter}...")
            return None
        inlasso = path.Path(verts).contains_points(np.column_stack((x_data,y_data)))
        self.view.scatterPlot.canvas.draw_idle()
        subDf = self.model.df[inlasso]
        self.model.selection = subDf
        logging.info(f"Lasso selected {len(subDf)} points.")
        self._switch_controls(True)
        self.update_scatter_plot()

    def save_selection(self):
        fname = save_dialog(self.view.dataframeLocation.text(), "PKL File (*.pkl)")
        self.model.df.to_pickle(fname)
        logging.info("Selection saved!")
            


