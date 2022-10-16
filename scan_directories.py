from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
import sys
from custom_thread import Worker


class ScanWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        size = QApplication.primaryScreen().size()
        self.setMinimumSize(QSize(size.width()//2, size.height()//2))
        self.setWindowTitle("Scan Directories")
        self.main_layout = QVBoxLayout()

        container = QWidget()
        container.setLayout(self.main_layout)

        self.pbar = QProgressBar(self)
        self.main_layout.addWidget(self.pbar)

        output = QWidget()
        self.output_layout = QVBoxLayout()
        output.setLayout(self.output_layout)
        self.output_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll = QScrollArea()
        scroll.setWidget(output)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        self.main_layout.addWidget(scroll)

        # create a custom thread
        self.worker = Worker()
        self.worker.countChanged.connect(self.changed)
        self.worker.finished.connect(self.finished)
        self.worker.output.connect(self.output)

        self.button = QPushButton()
        self.button.setText("Start")
        self.button.setMaximumWidth(size.width()//10)
        self.main_layout.addWidget(self.button)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.button.clicked.connect(self.update_progress)

        self.setCentralWidget(container)
        self.show()

    def update_progress(self):
        # show progress if thread is running else stop
        if not self.worker.isRunning():
            self.button.setText("Stop")
            self.worker.start()
        else:
            self.worker.terminate()
            self.button.setText("Start")

    def changed(self, count):
        self.pbar.setValue(count)

    def finished(self, output):
        self.worker.terminate()
        self.output(output)
        self.button.setText("Start")

    def output(self, output):
        label = QLabel()
        label.setText(output)
        label.setMaximumHeight(30)
        self.output_layout.addWidget(label)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    screen = app.primaryScreen()
    app.setStyle('Fusion')

    with open('style.qss', 'r') as f:
        style = f.read()
        app.setStyleSheet(style)

    window = ScanWindow()
    app.exec()
