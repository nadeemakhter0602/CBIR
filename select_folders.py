from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
import sys
import sqlite3


class ClickLabel(QLabel):
    clicked = pyqtSignal(str)

    def __init__(self, text):
        super().__init__()
        # storing text
        self.text = text

    def mouseDoubleClickEvent(self, ev):
        self.clicked.emit(self.text)


class SelectWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # create folders.db sqlite database
        self.folders = sqlite3.connect("folders.db")
        self.cur = self.folders.cursor()
        # create table which shall hold paths
        self.cur.execute("CREATE TABLE IF NOT EXISTS paths(path);")

        # set name of window
        self.setWindowTitle("Select the folders you want to index")
        # create a vertical box layout
        self.main_layout = QVBoxLayout()
        # set alignment of children to top
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # create a widget to hold list of paths
        path_list = QWidget()
        # set layout of the widget
        path_list.setLayout(self.main_layout)
        # get screen size
        size = QApplication.primaryScreen().size()
        # set minimum size of window
        self.setMinimumSize(QSize(size.width() // 2, size.height() // 2))
        # create toolbar
        toolbar = QToolBar()
        # add toolbar to MainWindow
        self.addToolBar(toolbar)

        # create an action
        addpath = QAction("Add new path", self)
        # create status tip of action
        addpath.setStatusTip("click to add new path")
        # add trigger to action
        addpath.triggered.connect(self.addpath_clicked)
        # add action to toolbar
        toolbar.addAction(addpath)

        # create another action
        save = QAction("Save", self)
        # create status tip of action
        save.setStatusTip("click to save all paths")
        # add trigger to action
        save.triggered.connect(self.save_list)
        # add action to toolbar
        toolbar.addAction(save)

        # set scrollable area
        scroll = QScrollArea()
        # set scrollable widget
        scroll.setWidget(path_list)
        # set parameters for scrolling
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)

        # show previously added paths
        for i in self.cur.execute("select path from paths;"):
            i = i[0]
            label = ClickLabel(i)
            label.setText(i)
            label.setMaximumHeight(30)
            label.clicked.connect(self.delete_from_list)
            label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            # add label to main_layout
            self.main_layout.addWidget(label)

        # set central widget
        self.setCentralWidget(scroll)
        self.show()

    def save_list(self, clicked):
        self.folders.commit()
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Saved!")
        dlg.setText("Saved all paths successfully!")
        dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
        dlg.exec()

    def addpath_clicked(self, clicked):
        # get folder select dialog
        folder_path = str(QFileDialog.getExistingDirectory(self, 'Select Folder'))
        # check database to see if folder_path was already added
        self.cur.execute("select count(*) from paths where path='{0}';".format(folder_path))
        count = self.cur.fetchall()[0][0]
        # show dialog if path was already added
        if count > 0:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText("The path already exists in list, please add another!")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
            return
        # insert folder_path to db
        self.cur.execute("insert into paths(path) values (?)", (folder_path,))
        # create a label and set params
        label = ClickLabel(folder_path)
        label.setText(folder_path)
        label.setMaximumHeight(30)
        label.clicked.connect(self.delete_from_list)
        label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # add label to main_layout
        self.main_layout.addWidget(label)

    def delete_from_list(self, text):
        print(text)
        self.cur.execute("delete from paths where path='{0}';".format(text))
        # delete everything and repopulate labels
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            widget.deleteLater()
        for i in self.cur.execute("select path from paths;"):
            i = i[0]
            label = ClickLabel(i)
            label.setText(i)
            label.setMaximumHeight(30)
            label.clicked.connect(self.delete_from_list)
            label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            # add label to main_layout
            self.main_layout.addWidget(label)


if __name__=='__main__':
    app = QApplication(sys.argv)
    screen = app.primaryScreen()
    app.setStyle('Fusion')

    with open('style.qss', 'r') as f:
        style = f.read()
        app.setStyleSheet(style)

    window = SelectWindow()
    app.exec()