from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from search import MainWindow
import sys


app = QApplication(sys.argv)
screen = app.primaryScreen()
app.setStyle('Fusion')

# load theme
with open('style.qss', 'r') as f:
    style = f.read()
    app.setStyleSheet(style)

# load icons
QDir.addSearchPath('icon', 'theme')

window = MainWindow(screen)
app.exec()