from PyQt6.QtWidgets import QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QLabel, QFrame, QCheckBox, QMessageBox
from PyQt6.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import numpy as np

from PyQt6 import QtCore, QtGui, QtWidgets
import sys

class MplCanvas(FigureCanvasQTAgg):
    """MPL/QT Canvas with some default characteristics and some axes."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

    def clear(self):
        self.axes.cla()

class PlotWithToolbar(QWidget):
    def __init__(self, title, autoscale = True):
        super().__init__()
        self.title = title
        self.wLayout = QVBoxLayout()
        self.canvas = MplCanvas(self)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.canvas.axes.set_title(title)
        self.canvas.axes.autoscale(autoscale)

        self.setLayout(self.wLayout)
        self.wLayout.addWidget(self.canvas)
        self.wLayout.addWidget(self.toolbar)

    def clear_axes(self):
        self.canvas.clear()
        self.label_x("")
        self.label_y("")
        self.canvas.axes.set_title(self.title)
        self.canvas.draw()

    def plot(self, x_data, y_data, **kwargs):
        artist = self.canvas.axes.plot(x_data, y_data, **kwargs)
        self.canvas.draw()
        return artist
    
    def scatter(self, x_data, y_data, **kwargs):
        artist = self.canvas.axes.scatter(x_data, y_data, **kwargs)
        self.canvas.draw()
        return artist
    
    def fill_between(self, x, y1, y2, **kwargs):
        poly = self.canvas.axes.fill_between(x,y1,y2,**kwargs)
        self.canvas.draw()
        return poly

    def label_x(self, new_label, **kwargs):
        self.canvas.axes.set_xlabel(new_label, **kwargs)
        self.canvas.draw()

    def label_y(self, new_label, **kwargs):
        self.canvas.axes.set_ylabel(new_label, **kwargs)
        self.canvas.draw()

    def update_toolbar(self):
        self.toolbar.update()

    def set_lims(self, top, bottom, left, right):
        self.canvas.axes.set_xlim(left, right)
        self.canvas.axes.set_ylim(bottom, top)
        self.canvas.draw()

    def update(self):
        self.canvas.draw()

class IOPanel(QWidget):
    """Input/Output panel class for input directory and output filepath selection."""
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        self._create_input_panel()
        self.layout.addWidget(VSeparator())
        self._create_output_panel()

    def _create_input_panel(self):
        """Initialises input side of IOPanel with a browse button and a line editor."""
        panel_title = QLabel("Input Directory")
        self.input_dir = QLineEdit()
        self.in_browse_button = QPushButton("Browse")

        self.input_layout = QVBoxLayout()
        self.input_layout.addWidget(panel_title)
        self.input_layout.addWidget(self.input_dir)
        self.input_layout.addWidget(self.in_browse_button)

        self.layout.addLayout(self.input_layout)

    def _create_output_panel(self):
        """Initialises output side of IOPanel with a browse button and a line editor."""
        panel_title = QLabel("Output Filepath")
        panel_title.setText("Output Filepath")
        self.output_path = QLineEdit()
        self.out_browse_button = QPushButton("Browse")

        self.output_layout = QVBoxLayout()
        self.output_layout.addWidget(panel_title)
        self.output_layout.addWidget(self.output_path)
        self.output_layout.addWidget(self.out_browse_button)

        self.layout.addLayout(self.output_layout)

    def get_input_dir(self) -> str:
        """Convenience method returns whatever is entered in input dir line edit."""
        return self.input_dir.text()

    def set_input_dir(self, text: str):
        """Convenience method sets input dir line edit text."""
        self.input_dir.setText(text)

    def get_output_path(self) -> str:
        """Convenience method gets whatever is in output path line edit."""
        return self.output_path.text()

    def set_output_path(self, text: str):
        """Convenience method sets output path line edit text."""
        self.output_path.setText(text)

    def lock(self):
        self.input_dir.setReadOnly(True)
        self.output_path.setReadOnly(True)
        self.in_browse_button.setEnabled(False)
        self.out_browse_button.setEnabled(False)

    def unlock(self):
        self.input_dir.setReadOnly(True)
        self.output_path.setReadOnly(True)
        self.in_browse_button.setEnabled(False)
        self.out_browse_button.setEnabled(False)

class PlotPanel(QWidget):
    """Widget with a left and right hand plot."""
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        self._create_left_plot()
        self.layout.addWidget(VSeparator())
        self._create_right_plot()


    def _create_left_plot(self):
        """Initialises left hand plot"""
        self.l_layout = QVBoxLayout()
        self.l_canvas = MplCanvas(self)
        self.l_label = QLabel("Trace Plot: ?/?")
        self.l_canvas.axes.autoscale(True)
        self.l_layout.addWidget(self.l_label)
        self.l_layout.addWidget(self.l_canvas)
        self.layout.addLayout(self.l_layout)

    def _create_right_plot(self):
        """Initialises right hand plot"""
        self.r_layout = QVBoxLayout()
        self.r_canvas = MplCanvas(self)
        self.r_label = QLabel("Event Plot: ?/?")
        self.r_canvas.axes.autoscale(True)
        self.r_layout.addWidget(self.r_label)
        self.r_layout.addWidget(self.r_canvas)
        self.layout.addLayout(self.r_layout)

    def l_clear_and_plot(self, ydata, xdata = None, **kwargs):
        """Clear left hand plot and plot new data on it"""
        self.l_canvas.axes.cla()
        if xdata is None:
            self.l_canvas.axes.plot(ydata, **kwargs)
        else:
            self.l_canvas.axes.plot(xdata, ydata, **kwargs)
        self.l_canvas.draw()
        

    def r_clear_and_plot(self, ydata, xdata = None, **kwargs):
        """Clear right hand plot and plot new data on it"""
        self.r_canvas.axes.cla()
        if xdata is None:
            self.r_canvas.axes.plot(ydata, **kwargs)
        else:
            self.r_canvas.axes.plot(xdata, ydata, **kwargs)
        self.r_canvas.draw()

    def r_vline(self, x, **kwargs):
        """Add vline to right hand plot at specified x"""
        self.r_canvas.axes.axvline(x, **kwargs)
        self.r_canvas.draw()

    def l_vline(self, x, **kwargs):
        """Add vline to left hand plot at specified x"""
        self.l_canvas.axes.axvline(x, **kwargs)
        self.l_canvas.draw()

    def set_r_label(self, str: str):
        self.r_label.setText(str)

    def set_l_label(self, str: str):
        self.l_label.setText(str)
    
class MainWindow(QMainWindow):
    closed = pyqtSignal()
    def __init__(self, title: str):
        """Initialise main window layout and sublayouts."""
        super().__init__()
        self.setWindowTitle(title)
        widget = QWidget()
        self.mainLayout = QVBoxLayout()
        widget.setLayout(self.mainLayout)
        self.setCentralWidget(widget)
        self._initialise_IO()
        self.mainLayout.addWidget(HSeparator())
        self._initialise_plots()
        self.mainLayout.addWidget(HSeparator())
        self._initialise_settings_and_controls()

        self.show()

    def _initialise_IO(self):
        """Initialise IO panel for choosing directory containing tdms files."""
        IOLayout = QHBoxLayout()
        #LABELS
        self.inputLabel = QLabel("Choose directory containing .tdms files for extraction:")
        #LINE EDITS
        self.inputLineEdit = QLineEdit()
        #BUTTONS
        self.browseButton = QPushButton(text="Browse")
        self.startButton = QPushButton(text="Validate Choice and Start")
        #PACKING
        IOLayout.addWidget(self.inputLabel)
        IOLayout.addWidget(self.inputLineEdit)
        IOLayout.addWidget(self.browseButton)
        IOLayout.addWidget(VSeparator())
        IOLayout.addWidget(self.startButton)
        #PACK INTO MAIN LAYOUT
        self.mainLayout.addLayout(IOLayout)

    def _initialise_plots(self):
        """Initialise plots panel containing trace plot and event plot."""
        PlotsLayout = QHBoxLayout()
        #PLOTS
        self.tracePlot = PlotWithToolbar("Trace Plot")
        self.eventPlot = PlotWithToolbar("Event Plot")
        #PACK
        PlotsLayout.addWidget(self.tracePlot)
        PlotsLayout.addWidget(VSeparator())
        PlotsLayout.addWidget(self.eventPlot)
        #PACK INTO MAIN LAYOUT
        self.mainLayout.addLayout(PlotsLayout)

    def _initialise_settings_and_controls(self):
        """Initialise settings and control panel containing settings and controls."""
        #LAYOUTS
        PanelLayout = QHBoxLayout()
        StartUpSettingsLayout = QVBoxLayout()
        ControlsLayout = QGridLayout()
        #LABELS
        self.settingsLabel = QLabel("Extractor Settings (Locked on pressing Start)")
        self.controlsLabel = QLabel("Controls")
        self.controlsLabel.setFixedHeight(10)
        #SETTINGS FIELDS
        self.sampleRateSetting = SettingField("Measurement Sample Rate:")
        self.eventThresholdSetting = SettingField("Event Threshold /nA:")
        self.eventBerthSetting = SettingField("Event Berth (Gap Each Side) /samples:")
        self.gapTolSetting = SettingField("Gap Tolerance (Max No. of Samples Below Threshold in Event):")
        #CONTROLS
        self.acceptButton = QPushButton(text="Accept Event")
        self.rejectButton = QPushButton(text="Reject Event")
        self.keepAcceptingButton = QPushButton(text="Keep Accepting")
        self.keepRejectingButton = QPushButton(text="Keep Rejecting")
        self.pauseButton = QPushButton("Pause")
        self.turboMode = QPushButton("Toggle Turbo Mode (Turn On/Off Plotting)")
        #LOOP DELAY SETTING
        self.loopDelaySetting = SettingField("Loop Delay /ms")
        #PACK SETTINGS
        StartUpSettingsLayout.addWidget(self.settingsLabel)
        StartUpSettingsLayout.addWidget(self.sampleRateSetting)
        StartUpSettingsLayout.addWidget(self.eventThresholdSetting)
        StartUpSettingsLayout.addWidget(self.eventBerthSetting)
        StartUpSettingsLayout.addWidget(self.gapTolSetting)
        #PACK CONTROLS
        ControlsLayout.addWidget(self.controlsLabel,0,0,1,2)
        ControlsLayout.addWidget(self.turboMode,1,1,1,2)
        ControlsLayout.addWidget(self.acceptButton,2,1)
        ControlsLayout.addWidget(self.rejectButton,2,2)
        ControlsLayout.addWidget(self.keepAcceptingButton,3,1)
        ControlsLayout.addWidget(self.keepRejectingButton,3,2)
        ControlsLayout.addWidget(self.pauseButton,4,1,1,2)
        ControlsLayout.addWidget(HSeparator(), 5, 1, 1, 2)
        ControlsLayout.addWidget(self.loopDelaySetting,6,1,1,2)
        #PACK LAYOUT
        PanelLayout.addLayout(StartUpSettingsLayout)
        PanelLayout.addWidget(VSeparator())
        PanelLayout.addLayout(ControlsLayout)
        self.mainLayout.addLayout(PanelLayout)
        #PACKAGE SETTINGS INTO LIST FOR EASY READING
        self.settings = [self.sampleRateSetting,self.eventThresholdSetting, self.eventBerthSetting, self.gapTolSetting]
        self.setting_names = ["sample_rate", "event_thresh", "event_berth", "gap_tol"]

    def get_all_settings(self) -> dict:
        """Get value of every setting and return in dictionary"""
        settings_dict={}
        for (setting, name) in (self.settings, self.setting_names):
            settings_dict[name]=setting.get_val()
        return settings_dict

    def lock_IO_panel(self):
        #Disable buttons
        self.browseButton.setEnabled(False)
        self.startButton.setEnabled(False)
        #Disable line edit
        self.inputLineEdit.setReadOnly(True)

    def unlock_IO_panel(self):
        #Enable buttons
        self.browseButton.setEnabled(True)
        self.startButton.setEnabled(True)
        #Disable line edit
        self.inputLineEdit.setReadOnly(False)

    def lock_start_settings(self):
        pass

    def unlock_start_settings(self):
        pass

    def lock_controls_loop(self):
        pass

    def unlock_controls_loop(self):
        pass

    def closeEvent(self,_):
        """Causes window to emit 'closed' signal when closed"""
        self.closed.emit()

class HSeparator(QFrame):
    """Horizontal line separator"""
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)

class VSeparator(QFrame):
    """Vertical line separator"""
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.VLine)

class SettingField(QWidget):
    """A widget comprised of a label/field pair."""
    def __init__(self, label: str, field_type: str = 'line'):
        super().__init__()
        self.widget_layout = QHBoxLayout()
        self.setLayout(self.widget_layout)
        self.label = QLabel(label)
        self.type = field_type
        if field_type == "line":
            self.field = QLineEdit()
        elif field_type == "check":
            self.field = QCheckBox()
        else:
            raise ValueError(f"Invalid argument, field type should be 'line' or 'check', not {field_type}")

        self.widget_layout.addWidget(self.label)
        self.widget_layout.addWidget(self.field)
    
    def get_val(self):
        """Get value of field"""
        if self.type == 'line':
            return self.field.text()
        elif self.type == 'check':
            return self.field.isChecked()

    def set_val(self, val):
        """Set value of field"""
        if self.type == 'line':
            self.field.setText(str(val))
        elif self.type == 'check':
            self.field.setChecked(val)

    def lock_field(self):
        self.field.setEnabled(False)

    def unlock_field(self):
        self.field.setEnabled(True)

    def field_name(self) -> str:
        """Get name of field"""
        return self.label.text()

    def __repr__(self) ->str:
        return f"Setting Field of type {self.type} with label {self.field_name()} and current value {self.get_val()}"

class ErrorDialog(QMessageBox):
    def __init__(self, msg: str):
        super().__init__()
        self.setWindowTitle("Error")
        self.setText(msg)
        self.exec()

class AllDone(QMessageBox):
    def __init__(self, msg: str):
        super().__init__()
        self.setWindowTitle("Finished")
        self.setText(msg)
        self.exec()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow("Hey")
    app.exec()