from PyQt6.QtWidgets import QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QLabel, QFrame, QCheckBox, QMessageBox
from PyQt6.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import numpy as np

from PyQt6 import QtCore, QtGui, QtWidgets
import sys

class MplCanvas(FigureCanvasQTAgg):
    """MPL/QT Canvas with some default characteristics and some axes."""
    def __init__(self, parent=None, width=5, height=10, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.tight_layout()
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

    def set_title(self, title: str):
        self.canvas.axes.set_title(title)
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
        StartUpSettingsLayout.addStretch()
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
        ControlsLayout.setRowStretch(ControlsLayout.rowCount(),1)
        #PACK LAYOUT
        PanelLayout.addLayout(StartUpSettingsLayout)
        PanelLayout.addWidget(VSeparator())
        PanelLayout.addLayout(ControlsLayout)
        self.mainLayout.addLayout(PanelLayout)
        #PACKAGE SETTINGS INTO LIST FOR EASY READING
        self.settings = [self.sampleRateSetting,self.eventThresholdSetting, self.eventBerthSetting, self.gapTolSetting, self.loopDelaySetting]
        self.setting_names = ["sample_rate", "event_thresh", "event_berth", "gap_tol", "loop_delay"]
        self.settings_dict = dict(zip(self.setting_names,self.settings))
        #PACKAGE CONTROLS INTO LIST FOR EASY HANDLING
        self.controls = [self.acceptButton, self.rejectButton,self.keepAcceptingButton,self.keepRejectingButton, self.pauseButton, self.turboMode]

    def get_all_settings(self) -> dict[str,'SettingField']:
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
        """Lock all settings except last one (Which should be the loop delay setting)"""
        for setting in self.settings[:-1]: 
            setting.lock_field()

    def unlock_start_settings(self):
        """Unock all settings except last one (Which should be the loop delay setting)"""
        for setting in self.settings[:-1]: 
            setting.unlock_field()

    def lock_controls_loop(self):
        """Locks all controls except Pause and Turbo Mode which should remain available in the loop"""
        for control in self.controls[:-2]:
            control.setEnabled(False)
        self.loopDelaySetting.lock_field()

    def unlock_controls_loop(self):
        """Unlocks all controls usually locked in the loop (Pause and Turbo Mode)"""
        for control in self.controls[:-2]:
            control.setEnabled(True)
        self.loopDelaySetting.unlock_field()

    def lock_all_controls(self):
        for control in self.controls:
            control.setEnabled(False)
        self.loopDelaySetting.lock_field()
    
    def unlock_all_controls(self):
        for control in self.controls:
            control.setEnabled(True)
        self.loopDelaySetting.unlock_field()

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
        if self.type == 'line':
            self.field.setReadOnly(True)
        else:
            self.field.setEnabled(False)

    def unlock_field(self):
        if self.type == 'line':
            self.field.setReadOnly(False)
        else:
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