from view import MainWindow
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
    w = MainWindow(title = "Extractor v2.0gamma")
    ctrlr = Controller(w,model)
    app.exec()