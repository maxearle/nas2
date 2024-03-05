from PyQt6.QtWidgets import QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QFrame, QComboBox, QMessageBox
from PyQt6.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from model import Point

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

    def plot_point(self, point: Point, **kwargs):
        artist = self.canvas.axes.plot(point.x, point.y, **kwargs)
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
    IOLayout = QHBoxLayout()
    plotsLayout = QHBoxLayout()
    controlsLayout = QHBoxLayout()
    mainLayout = QVBoxLayout()
    def __init__(self, version = None):
        super().__init__()
        self.setWindowTitle(f"Filter - v:{version}")
        widget = QWidget()
        widget.setLayout(self.mainLayout)
        self.setCentralWidget(widget)
        self._initialise_IO()
        self.mainLayout.addWidget(HSeparator())
        self._initialise_plots()
        self.mainLayout.addWidget(HSeparator())
        self._initialise_controls()

        self.show()
    
    #INITIALISATION
    def _initialise_IO(self):
        #Buttons
        self.chooseDfButton = QPushButton("Choose Input Dataframe")
        self.chooseDataButton = QPushButton("Choose Data (.hdf5)")
        self.startButton = QPushButton("Start")
        self.newButton = QPushButton("New Dataset")
        self.lockNameButton = QPushButton("Lock in Names")
        #Line entries
        self.dataLocation = QLineEdit()
        self.dataframeLocation = QLineEdit()
        #Labels
        dataLabel = QLabel("Data Source")
        dfLabel = QLabel("Dataframe")
        nameLabel = QLabel("Name Column")
        #Combobox
        self.nameBox = QComboBox()
        #Layout
        self.IOLayout.addWidget(self.startButton)
        self.IOLayout.addWidget(VSeparator())
        self.IOLayout.addWidget(dataLabel)
        self.IOLayout.addWidget(self.dataLocation)
        self.IOLayout.addWidget(self.chooseDataButton)
        self.IOLayout.addWidget(VSeparator())
        self.IOLayout.addWidget(dfLabel)
        self.IOLayout.addWidget(self.dataframeLocation)
        self.IOLayout.addWidget(self.chooseDfButton)
        self.IOLayout.addWidget(VSeparator())
        self.IOLayout.addWidget(nameLabel)
        self.IOLayout.addWidget(self.nameBox)
        self.IOLayout.addWidget(self.lockNameButton)
        self.IOLayout.addWidget(VSeparator())
        self.IOLayout.addWidget(self.newButton)

        self.mainLayout.addLayout(self.IOLayout)

    def _initialise_plots(self):
        #Canvases
        self.scatterPlot = PlotWithToolbar("Scatter Plot",autoscale=False)
        self.eventPlot = PlotWithToolbar("Selected Event")
        #Pack
        self.plotsLayout.addWidget(self.scatterPlot)
        self.plotsLayout.addWidget(VSeparator())
        self.plotsLayout.addWidget(self.eventPlot)

        self.mainLayout.addLayout(self.plotsLayout)

    def _initialise_controls(self):
        #Buttons
        self.chooseFirstButton = QPushButton("Choose Point 1")
        self.chooseSecButton = QPushButton("Choose Point 2")
        self.chooseRegionButton = QPushButton("Choose Plot Region to Save")
        self.resetAllButton = QPushButton("Reset All Choices")
        self.saveSelectionButton = QPushButton("Save Subset to Dataframe")
        self.updatePlotButton = QPushButton("Update Plot")
        #Labels
        xLabel = QLabel("x-Axis Parameter")
        yLabel = QLabel("y-Axis Parameter")
        #Comboboxes
        self.xBox = QComboBox()
        self.yBox = QComboBox()
        #Layout
        self.controlsLayout.addWidget(xLabel)
        self.controlsLayout.addWidget(self.xBox)
        self.controlsLayout.addWidget(yLabel)
        self.controlsLayout.addWidget(self.yBox)
        self.controlsLayout.addWidget(self.updatePlotButton)
        self.controlsLayout.addWidget(VSeparator())
        self.controlsLayout.addWidget(self.chooseFirstButton)
        self.controlsLayout.addWidget(self.chooseSecButton)
        self.controlsLayout.addWidget(self.chooseRegionButton)
        self.controlsLayout.addWidget(VSeparator())
        self.controlsLayout.addWidget(self.resetAllButton)
        self.controlsLayout.addWidget(self.saveSelectionButton)

        self.mainLayout.addLayout(self.controlsLayout)

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
