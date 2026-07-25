DARK_QSS = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 14px;
}

QListWidget {
    background-color: #16213e;
    border: none;
    border-right: 2px solid #0f3460;
    outline: none;
    padding: 8px;
}

QListWidget::item {
    padding: 12px 16px;
    border-radius: 8px;
    margin: 2px 4px;
    color: #a0a0b0;
}

QListWidget::item:selected {
    background-color: #0f3460;
    color: #00d9a3;
    font-weight: bold;
}

QListWidget::item:hover {
    background-color: #1a1a3e;
}

QStackedWidget {
    background-color: #1a1a2e;
}

QLabel {
    color: #e0e0e0;
    background: transparent;
}

QLabel#titleLabel {
    font-size: 22px;
    font-weight: bold;
    color: #00d9a3;
    padding: 10px;
}

QLabel#sectionLabel {
    font-size: 16px;
    font-weight: bold;
    color: #00d9a3;
    padding: 6px 0;
}

QLabel#statLabel {
    font-size: 13px;
    color: #a0a0b0;
}

QLabel#statValue {
    font-size: 15px;
    font-weight: bold;
    color: #e0e0e0;
}

QLabel#statusOk {
    color: #00d9a3;
    font-weight: bold;
}

QLabel#statusWarn {
    color: #ffaa00;
    font-weight: bold;
}

QLabel#statusError {
    color: #ff4444;
    font-weight: bold;
}

QPushButton {
    background-color: #0f3460;
    color: #e0e0e0;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 14px;
}

QPushButton:hover {
    background-color: #1a4a7a;
}

QPushButton:pressed {
    background-color: #0a2a50;
}

QPushButton#dangerBtn {
    background-color: #4a1525;
}

QPushButton#dangerBtn:hover {
    background-color: #6a2035;
}

QTextEdit {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 8px;
    padding: 12px;
    color: #e0e0e0;
    font-size: 14px;
}

QTextEdit#chatDisplay {
    background-color: #111122;
    border: none;
    border-radius: 12px;
}

QLineEdit {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    padding: 10px 14px;
    color: #e0e0e0;
    font-size: 14px;
}

QLineEdit:focus {
    border-color: #00d9a3;
}

QComboBox {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 6px;
    padding: 6px 12px;
    color: #e0e0e0;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 1px solid #0f3460;
    selection-background-color: #0f3460;
    color: #e0e0e0;
}

QScrollBar:vertical {
    background: #111122;
    width: 10px;
    border: none;
}

QScrollBar::handle:vertical {
    background: #0f3460;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #1a4a7a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QFrame#card {
    background-color: #16213e;
    border-radius: 12px;
    padding: 16px;
}

QFrame#separator {
    background-color: #0f3460;
    max-height: 1px;
}

QGroupBox {
    border: 1px solid #0f3460;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    color: #00d9a3;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QTableWidget {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 8px;
    gridline-color: #0f3460;
    color: #e0e0e0;
}

QTableWidget::item {
    padding: 6px;
}

QHeaderView::section {
    background-color: #0f3460;
    color: #00d9a3;
    border: none;
    padding: 8px;
    font-weight: bold;
}

QStatusBar {
    background-color: #111122;
    color: #a0a0b0;
    border-top: 1px solid #0f3460;
}
"""
