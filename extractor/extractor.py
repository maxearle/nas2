from view import MainWindow, IOPanel, PlotPanel, SettingsControlPanel
from controller import Controller
from model import Model
from PyQt6.QtWidgets import QApplication
import sys
import logging

#RUN THIS ONE

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    model = Model()
    io = IOPanel()
    plots = PlotPanel()
    settings = {
        "Sample Rate":(1000000, 'line'),
        "Event Threshold": (-0.06, 'line'),
        "Correct trace slope":(True, 'check'),
        "Gap tolerance":(1000, 'line'),
        "Event Berth": (1000, 'line'),
        "Loop delay": (50, 'line')
    }
    buttons = ["Start", "Accept event", "Reject event", "Keep accepting", "Keep rejecting", "Pause","Next batch", "Finish"]
    cfg = SettingsControlPanel(settings, buttons)
    w = MainWindow(title = "Extractor v2.0alpha",top = io,mid = plots,bott = cfg)
    ctrlr = Controller(w,model)
    app.exec()