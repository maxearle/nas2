import typing
from PyQt6 import QtGui
from PyQt6.QtWidgets import QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QLabel, QFrame, QComboBox, QMessageBox
from PyQt6.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

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
    
    def set_title(self, str):
        self.title = str
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

    def text(self,x,y,str, **kwargs):
        self.canvas.axes.text(x,y,str,**kwargs)
        self.canvas.draw()

    def update(self):
        self.canvas.draw()

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

class MainWindow(QMainWindow):
    closed = pyqtSignal()
    keyPressed = pyqtSignal(int)
    mainLayout = QVBoxLayout()
    IOLayout = QHBoxLayout()
    controlsLayout = QGridLayout()
    clicked = pyqtSignal()
    def __init__(self, version = ""):
        super().__init__()
        self.setWindowTitle(f"Assigner - Version: {version}")

        widget = QWidget()
        widget.setLayout(self.mainLayout)
        self.setCentralWidget(widget)
        self._initialise_IO()
        self.mainLayout.addWidget(HSeparator())
        self._initialise_plot()
        self.mainLayout.addWidget(HSeparator())
        self._initialise_controls()

        self.show()

    def keyPressEvent(self, event):
            super(QMainWindow,self).keyPressEvent(event)
            self.keyPressed.emit(event.key())

    #INITIALISATION
    def _initialise_IO(self):
        #Buttons
        self.chooseDfButton = QPushButton("Choose Assignments Dataframe (if one exists)")
        self.chooseDataButton = QPushButton("Choose Data (.hdf5)")
        self.startButton = QPushButton("Start")
        #Line entries
        self.dataLocation = QLineEdit()
        self.dataframeLocation = QLineEdit()
        self.poiList = QLineEdit()
        #Labels
        dataLabel = QLabel("Data Source")
        dfLabel = QLabel("Assignments Dataframe")
        poiLabel = QLabel("Peaks of Interest (POIs) (peak1,1;peak2,2;peak3,3 e.g.)")
        #Combobox
        self.nameBox = QComboBox()
        #Layout
        self.IOLayout.addWidget(dataLabel)
        self.IOLayout.addWidget(self.dataLocation)
        self.IOLayout.addWidget(self.chooseDataButton)
        self.IOLayout.addWidget(VSeparator())
        self.IOLayout.addWidget(dfLabel)
        self.IOLayout.addWidget(self.dataframeLocation)
        self.IOLayout.addWidget(self.chooseDfButton)
        self.IOLayout.addWidget(VSeparator())
        self.IOLayout.addWidget(poiLabel)
        self.IOLayout.addWidget(self.poiList)
        self.IOLayout.addWidget(VSeparator())
        self.IOLayout.addWidget(self.startButton)

        self.mainLayout.addLayout(self.IOLayout)

    def _initialise_plot(self):
        #Canvas
        self.eventPlot = PlotWithToolbar("Event Plot", autoscale=False)
        #Pack
        self.mainLayout.addWidget(self.eventPlot)

    def _initialise_controls(self):
        #Buttons
        self.prevButton = QPushButton("Previous Event (,)")
        self.nextButton = QPushButton("Next Event (.)")
        self.acceptButton = QPushButton("Accept Assignment (A)")
        self.rejectButton = QPushButton("Reject Assignment (R)")
        self.saveButton = QPushButton("Save Assignments (S)")
        self.lineLabel = QLabel("Alternative Assignment")
        self.altAssEntry = QLineEdit()
        self.enterButton = QPushButton("Use Alt Assignment (Enter)")
        #Pack
        self.controlsLayout.addWidget(self.prevButton,0,0)
        self.controlsLayout.addWidget(self.acceptButton,0,1)
        self.controlsLayout.addWidget(self.rejectButton,0,2)
        self.controlsLayout.addWidget(self.saveButton,0,3)
        self.controlsLayout.addWidget(self.nextButton,0,4)
        self.controlsLayout.addWidget(self.lineLabel,1,0)
        self.controlsLayout.addWidget(self.altAssEntry,1,1,1,3)
        self.controlsLayout.addWidget(self.enterButton,1,4)

        self.mainLayout.addLayout(self.controlsLayout)

    def disable_all_controls(self):
        self.prevButton.setEnabled(False)
        self.nextButton.setEnabled(False)
        self.acceptButton.setEnabled(False)
        self.rejectButton.setEnabled(False)
        self.altAssEntry.setReadOnly(True)
        self.enterButton.setEnabled(False)
        self.saveButton.setEnabled(False)

    def enable_all_controls(self):
        self.prevButton.setEnabled(True)
        self.nextButton.setEnabled(True)
        self.acceptButton.setEnabled(True)
        self.rejectButton.setEnabled(True)
        self.altAssEntry.setReadOnly(False)
        self.enterButton.setEnabled(True)
        self.saveButton.setEnabled(True)

    def enable_io(self):
        self.chooseDfButton.setEnabled(True)
        self.chooseDataButton.setEnabled(True)
        self.startButton.setEnabled(True)


        self.dataLocation.setReadOnly(False)
        self.dataframeLocation.setReadOnly(False)
        self.poiList.setReadOnly(False)

    def disable_io(self):
        self.chooseDfButton.setEnabled(False)
        self.chooseDataButton.setEnabled(False)
        self.startButton.setEnabled(False)


        self.dataLocation.setReadOnly(True)
        self.dataframeLocation.setReadOnly(True)
        self.poiList.setReadOnly(True)

    def mousePressEvent(self, event):
        self.clicked.emit()

    def closeEvent(self, event):
        self.closed.emit()
        event.accept()

class ErrorDialog(QMessageBox):
    def __init__(self, msg: str):
        super().__init__()
        self.setWindowTitle("Error")
        self.setText(msg)
        self.exec()

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = MainWindow(version = "Layout test")
    app.exec()