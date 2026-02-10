import sys
from datetime import date, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QCalendarWidget, QFrame, QStackedWidget,
                             QSpinBox, QComboBox, QDateEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QProgressBar, QScrollArea, QMessageBox, QTabWidget)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor

from backend.attendance_backend import AttendanceBrain

STYLESHEET = """
QMainWindow { background-color: #000000; }
QWidget { background-color: #000000; color: #EDEDED; font-family: 'Segoe UI', sans-serif; }
QFrame[class="Card"] { background-color: #0A0A0A; border: 1px solid #333333; border-radius: 8px; }
QFrame#Sidebar { background-color: #050505; border-right: 1px solid #333333; }
QLabel[class="Header"] { font-size: 24px; font-weight: 700; color: #FFFFFF; }
QLabel[class="SubHeader"] { font-size: 13px; font-weight: 600; color: #888888; text-transform: uppercase; }
QLabel[class="Label"] { font-size: 14px; color: #CCCCCC; }
QLabel[objectName="StatValue"] { font-size: 32px; font-weight: 700; color: #FFFFFF; }
QPushButton { background-color: #000000; color: #EDEDED; border: 1px solid #333333; padding: 10px; border-radius: 6px; font-weight: 600; }
QPushButton:hover { background-color: #111111; border-color: #666666; }
QPushButton[class="Primary"] { background-color: #ededed; color: #000000; border: 1px solid #ededed; }
QPushButton[class="Auto"] { background-color: #0070F3; color: white; border: none; }
QSpinBox, QComboBox, QDateEdit { background-color: #0A0A0A; border: 1px solid #333333; padding: 8px; border-radius: 6px; color: white; }
QTableWidget { background-color: #0A0A0A; border: 1px solid #333; gridline-color: #222; }
QHeaderView::section { background-color: #111; padding: 4px; border: none; color: #888; }
QProgressBar { border: none; background-color: #222; height: 6px; border-radius: 3px; }
QProgressBar::chunk { background-color: #0070F3; border-radius: 3px; }
QTabWidget::pane { border: 1px solid #333; }
QTabBar::tab { background: #111; color: #888; padding: 8px 15px; }
QTabBar::tab:selected { background: #222; color: white; border-bottom: 2px solid #0070F3; }
"""


class DateHeatmap(QCalendarWidget):
    def __init__(self, brain):
        super().__init__()
        self.brain = brain
        self.setGridVisible(False)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        if self.brain.is_trained:
            py_date = date.toPyDate()
            if py_date >= date.currentDate().toPyDate():
                risk = self.brain.predict_day_risk(py_date)
                if risk > 0.6:
                    painter.fillRect(rect, QColor(255, 0, 80, 80))
                elif risk > 0.3:
                    painter.fillRect(rect, QColor(245, 166, 35, 80))


# --- NEW VISUAL: TIMETABLE HEATMAP ---
class TimetableHeatmap(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])
        self.verticalHeader().setVisible(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def update_data(self, brain):
        self.clearContents()
        risk_matrix = brain.get_slot_risk_matrix()  # {(DayIdx, Time): Risk}
        timetable = brain.timetable

        # 1. Collect all unique time slots from timetable
        all_times = set()
        for day, slots in timetable.items():
            all_times.update(slots.keys())

        sorted_times = sorted(list(all_times))
        if not sorted_times: return  # No data yet

        self.setRowCount(len(sorted_times))
        self.setVerticalHeaderLabels(sorted_times)

        for r, time_str in enumerate(sorted_times):
            for c in range(6):  # Mon=0 to Sat=5
                # Get Subject Name
                subj_name = ""
                if c in timetable and time_str in timetable[c]:
                    subj_name = timetable[c][time_str]

                # Get Risk
                risk = risk_matrix.get((c, time_str), 0)

                item = QTableWidgetItem(subj_name)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Coloring
                if subj_name:
                    if risk > 0.5:
                        item.setBackground(QColor(200, 50, 50, 150))  # Red
                        item.setToolTip(f"High Absence Risk: {int(risk * 100)}%")
                    elif risk > 0.2:
                        item.setBackground(QColor(200, 160, 50, 150))  # Yellow
                        item.setToolTip(f"Moderate Risk: {int(risk * 100)}%")
                    else:
                        item.setBackground(QColor(50, 150, 50, 100))  # Green
                        item.setToolTip("Good Attendance")
                else:
                    item.setForeground(QColor("#444"))  # Empty slot

                self.setItem(r, c, item)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.brain = AttendanceBrain()
        self.setWindowTitle("Attendance...")
        self.resize(1300, 950)
        self.setStyleSheet(STYLESHEET)
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)
        sb_layout = QVBoxLayout(sidebar)

        lbl_t = QLabel("YOU\nAGAIN?\n")
        lbl_t.setProperty("class", "Header")
        sb_layout.addWidget(lbl_t)

        self.btn_dash = QPushButton("Dashboard")
        self.btn_dash.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        sb_layout.addWidget(self.btn_dash)

        self.btn_plan = QPushButton("Calculator & Forecast")
        self.btn_plan.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        sb_layout.addWidget(self.btn_plan)

        sb_layout.addSpacing(20)

        lbl_src = QLabel("DATA SOURCE")
        lbl_src.setProperty("class", "SubHeader")
        sb_layout.addWidget(lbl_src)

        self.btn_tt = QPushButton("1. Load Timetable")
        self.btn_tt.clicked.connect(self.load_timetable)
        sb_layout.addWidget(self.btn_tt)

        self.btn_daily = QPushButton("2. Load Absence Details")
        self.btn_daily.clicked.connect(self.load_absence_details)
        sb_layout.addWidget(self.btn_daily)

        self.btn_summary = QPushButton("3. Load Attendance Details")
        self.btn_summary.clicked.connect(self.load_summary)
        sb_layout.addWidget(self.btn_summary)

        self.lbl_status = QLabel("System Ready")
        self.lbl_status.setStyleSheet("color: #444; font-size: 12px; margin-top:10px;")
        self.lbl_status.setWordWrap(True)
        sb_layout.addWidget(self.lbl_status)
        sb_layout.addStretch()

        self.stack = QStackedWidget()
        self.page_dash = QWidget()
        self.setup_dashboard(self.page_dash)
        self.stack.addWidget(self.page_dash)

        self.page_plan = QWidget()
        self.setup_planner(self.page_plan)
        self.stack.addWidget(self.page_plan)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack)

    def setup_dashboard(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(32, 32, 32, 32)

        header = QHBoxLayout()
        l_ov = QLabel("Overview")
        l_ov.setProperty("class", "Header")
        header.addWidget(l_ov)
        header.addStretch()
        self.badge_pct = QLabel("Waiting...")
        self.badge_pct.setStyleSheet("background: #111; color: #666; padding: 5px 15px; border-radius: 15px;")
        header.addWidget(self.badge_pct)
        layout.addLayout(header)

        row1 = QHBoxLayout()

        # --- TABBED VISUALS ---
        cal_card = QFrame()
        cal_card.setProperty("class", "Card")
        cal_layout = QVBoxLayout(cal_card)
        l_hm = QLabel("VISUAL INTELLIGENCE")
        l_hm.setProperty("class", "SubHeader")
        cal_layout.addWidget(l_hm)

        self.tabs = QTabWidget()
        self.cal_view = DateHeatmap(self.brain)
        self.time_view = TimetableHeatmap()

        self.tabs.addTab(self.cal_view, "Date Calendar")
        self.tabs.addTab(self.time_view, "Timetable Risk")

        cal_layout.addWidget(self.tabs)
        row1.addWidget(cal_card, stretch=3)

        # Risk List
        risk_card = QFrame()
        risk_card.setProperty("class", "Card")
        risk_layout = QVBoxLayout(risk_card)
        l_sh = QLabel("SUBJECT HEALTH")
        l_sh.setProperty("class", "SubHeader")
        risk_layout.addWidget(l_sh)

        self.risk_container = QWidget()
        self.risk_box = QVBoxLayout(self.risk_container)
        self.risk_box.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.risk_container)
        scroll.setStyleSheet("background: transparent; border: none;")
        risk_layout.addWidget(scroll)
        row1.addWidget(risk_card, stretch=2)

        layout.addLayout(row1)

    def setup_planner(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(32, 32, 32, 32)
        l_cf = QLabel("Calculator & Forecast")
        l_cf.setProperty("class", "Header")
        layout.addWidget(l_cf)

        calc_card = QFrame()
        calc_card.setProperty("class", "Card")
        calc_layout = QVBoxLayout(calc_card)

        self.btn_auto = QPushButton("⚡ AUTO FILL & CALCULATE")
        self.btn_auto.setProperty("class", "Auto")
        self.btn_auto.setVisible(False)
        self.btn_auto.clicked.connect(self.run_auto_calc)
        calc_layout.addWidget(self.btn_auto)

        inputs = QHBoxLayout()
        grp1 = QVBoxLayout()
        l_t = QLabel("Total Classes")
        l_t.setProperty("class", "Label")
        grp1.addWidget(l_t)
        self.spin_total = QSpinBox()
        self.spin_total.setRange(0, 5000)
        grp1.addWidget(self.spin_total)
        inputs.addLayout(grp1)

        grp2 = QVBoxLayout()
        l_a = QLabel("Absent Classes")
        l_a.setProperty("class", "Label")
        grp2.addWidget(l_a)
        self.spin_absent = QSpinBox()
        self.spin_absent.setRange(0, 5000)
        grp2.addWidget(self.spin_absent)
        inputs.addLayout(grp2)

        grp3 = QVBoxLayout()
        l_tg = QLabel("Target %")
        l_tg.setProperty("class", "Label")
        grp3.addWidget(l_tg)
        self.spin_target = QSpinBox()
        self.spin_target.setRange(1, 100)
        self.spin_target.setValue(75)
        grp3.addWidget(self.spin_target)
        inputs.addLayout(grp3)
        calc_layout.addLayout(inputs)

        # Date
        date_row = QHBoxLayout()
        grp_d1 = QVBoxLayout()
        lbl_sd = QLabel("Start Date:")
        lbl_sd.setProperty("class", "Label")
        grp_d1.addWidget(lbl_sd)
        self.combo_start = QComboBox()
        self.combo_start.addItems(["Start Today", "Custom Date"])
        self.combo_start.currentIndexChanged.connect(
            lambda: self.date_edit_start.setVisible(self.combo_start.currentIndex() == 1))
        self.date_edit_start = QDateEdit()
        self.date_edit_start.setCalendarPopup(True)
        self.date_edit_start.setDate(QDate.currentDate())
        self.date_edit_start.setVisible(False)
        d1_c = QHBoxLayout()
        d1_c.addWidget(self.combo_start)
        d1_c.addWidget(self.date_edit_start)
        grp_d1.addLayout(d1_c)
        date_row.addLayout(grp_d1)

        grp_d2 = QVBoxLayout()
        lbl_ed = QLabel("Limit Forecast To:")
        lbl_ed.setProperty("class", "Label")
        grp_d2.addWidget(lbl_ed)
        self.combo_end = QComboBox()
        self.combo_end.addItems(["6 Months", "Semester End (Auto)", "Custom Date"])
        self.combo_end.currentIndexChanged.connect(
            lambda: self.date_edit_end.setVisible(self.combo_end.currentIndex() == 2))
        self.date_edit_end = QDateEdit()
        self.date_edit_end.setCalendarPopup(True)
        self.date_edit_end.setDate(QDate.currentDate().addMonths(6))
        self.date_edit_end.setVisible(False)
        d2_c = QHBoxLayout()
        d2_c.addWidget(self.combo_end)
        d2_c.addWidget(self.date_edit_end)
        grp_d2.addLayout(d2_c)
        date_row.addLayout(grp_d2)
        date_row.addStretch()

        btn_calc = QPushButton("Calculate Forecast")
        btn_calc.setProperty("class", "Primary")
        btn_calc.setFixedSize(180, 40)
        btn_calc.clicked.connect(self.calculate_plan)
        date_row.addWidget(btn_calc)
        calc_layout.addLayout(date_row)
        layout.addWidget(calc_card)

        res_row = QHBoxLayout()
        self.res_action = self.create_stat("ACTION PLAN", "Ready...", wide=True)
        self.res_timeline = self.create_stat("TIMELINE", "--")
        res_row.addWidget(self.res_action, stretch=2)
        res_row.addWidget(self.res_timeline, stretch=1)
        layout.addLayout(res_row)

        self.table_card = QFrame()
        self.table_card.setProperty("class", "Card")
        table_lay = QVBoxLayout(self.table_card)
        l_rs = QLabel("RECOVERY SCHEDULE")
        l_rs.setProperty("class", "SubHeader")
        table_lay.addWidget(l_rs)

        self.sched_table = QTableWidget()
        self.sched_table.setColumnCount(4)
        self.sched_table.setHorizontalHeaderLabels(["Date", "Day", "Time", "Subject"])
        self.sched_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sched_table.verticalHeader().setVisible(False)
        self.sched_table.setShowGrid(False)
        table_lay.addWidget(self.sched_table)
        layout.addWidget(self.table_card)

    def create_stat(self, title, val, wide=False):
        w = QFrame()
        w.setProperty("class", "Card")
        l = QVBoxLayout(w)
        l_t = QLabel(title)
        l_t.setProperty("class", "SubHeader")
        l.addWidget(l_t)
        v = QLabel(val)
        v.setObjectName("StatValue")
        v.setWordWrap(True)
        if wide: v.setStyleSheet("font-size: 24px; color: white;")
        l.addWidget(v)
        return w

    def load_timetable(self):
        path, _ = QFileDialog.getOpenFileName(self, "Timetable", "", "CSV (*.csv)")
        if path:
            ok, msg = self.brain.parse_timetable(path)
            self.lbl_status.setText(msg)
            if ok:
                self.btn_tt.setStyleSheet("border: 1px solid #0070F3; color: #0070F3;")
                self.time_view.update_data(self.brain)  # Refresh view

    def load_absence_details(self):
        path, _ = QFileDialog.getOpenFileName(self, "Absence Details", "", "CSV (*.csv)")
        if path:
            ok, msg = self.brain.load_absence_details(path)
            self.lbl_status.setText(msg)
            if ok:
                self.btn_daily.setStyleSheet("border: 1px solid #0070F3; color: #0070F3;")
                self.cal_view.updateCell(QDate.currentDate())
                self.time_view.update_data(self.brain)  # Refresh view
                self.refresh_dashboard_widgets()

    def load_summary(self):
        path, _ = QFileDialog.getOpenFileName(self, "Attendance Details", "", "CSV (*.csv)")
        if path:
            ok, msg = self.brain.parse_attendance_summary(path)
            self.lbl_status.setText(msg)
            if ok:
                self.btn_summary.setStyleSheet("border: 1px solid #0070F3; color: #0070F3;")
                self.btn_auto.setVisible(True)
                self.btn_auto.setText(f"⚡ AUTO FILL ({self.brain.auto_total} / {self.brain.auto_absent})")
                self.refresh_dashboard_widgets()

    def refresh_dashboard_widgets(self):
        self.time_view.update_data(self.brain)

        for i in reversed(range(self.risk_box.count())):
            self.risk_box.itemAt(i).widget().setParent(None)

        risks = self.brain.get_subject_risks()
        for subj, score in risks:
            w = QWidget()
            l = QVBoxLayout(w)
            l.setContentsMargins(0, 5, 0, 5)
            header = QHBoxLayout()
            header.addWidget(QLabel(subj, styleSheet="font-weight: bold;"))
            header.addStretch()
            header.addWidget(
                QLabel("High Absence" if score > 0.5 else "Moderate", styleSheet="color:#666; font-size:11px;"))
            l.addLayout(header)
            bar = QProgressBar()
            bar.setValue(int(score * 100))
            if score > 0.7:
                bar.setStyleSheet("QProgressBar::chunk { background-color: #FF0050; }")
            elif score > 0.4:
                bar.setStyleSheet("QProgressBar::chunk { background-color: #F5A623; }")
            else:
                bar.setStyleSheet("QProgressBar::chunk { background-color: #0070F3; }")
            l.addWidget(bar)
            self.risk_box.addWidget(w)

    def run_auto_calc(self):
        try:
            if self.brain.has_summary_data:
                self.spin_total.setValue(self.brain.auto_total)
                self.spin_absent.setValue(self.brain.auto_absent)
                self.calculate_plan()
        except Exception as e:
            QMessageBox.critical(self, "Auto Error", str(e))

    def calculate_plan(self):
        try:
            tot = self.spin_total.value()
            absent = self.spin_absent.value()
            target = self.spin_target.value()
            start = date.today()
            if self.combo_start.currentIndex() == 1: start = self.date_edit_start.date().toPyDate()

            mode = self.combo_end.currentIndex()
            if mode == 0:
                limit = start + timedelta(days=180)
            elif mode == 1:
                limit = self.brain.get_semester_end_date(start)
            else:
                limit = self.date_edit_end.date().toPyDate()

            res = self.brain.calculate_recovery_plan(target, tot, absent, start, limit)

            if tot > 0: self.badge_pct.setText(f"CURRENT: {res['current_pct']:.1f}%")

            act_lbl = self.res_action.findChild(QLabel, "StatValue")
            time_lbl = self.res_timeline.findChild(QLabel, "StatValue")
            self.sched_table.setRowCount(0)

            if res['status'] == 'impossible':
                act_lbl.setText("Impossible Target")
                time_lbl.setText("Mathematics check failed")
            elif res['status'] == 'no_classes_found':
                act_lbl.setText("No Classes Found")
                time_lbl.setText("Timetable mismatch/empty")
            elif res['status'] == 'impossible_timeframe':
                max_p = res.get('max_possible', 0)
                end_str = res['end_date'].strftime('%d %b %Y')
                act_lbl.setText(f"IMPOSSIBLE BY {end_str}")
                time_lbl.setText(f"Max Possible: {max_p:.1f}%")
                if 'schedule' in res:
                    for item in res['schedule']:
                        row = self.sched_table.rowCount()
                        self.sched_table.insertRow(row)
                        self.sched_table.setItem(row, 0, QTableWidgetItem(item['Date'].strftime("%d-%m")))
                        self.sched_table.setItem(row, 1, QTableWidgetItem(item['Day']))
                        self.sched_table.setItem(row, 2, QTableWidgetItem(item['Time']))
                        self.sched_table.setItem(row, 3, QTableWidgetItem(item['Subject']))

            elif res['status'] == 'surplus':
                act_lbl.setText(f"SAFE: Skip {res['classes_skippable']}")
                time_lbl.setText("Target Met")
            elif res['status'] == 'deficit':
                act_lbl.setText(f"ATTEND {res['classes_needed']} CLASSES")
                if 'days_needed' in res:
                    end_str = res['end_date'].strftime('%d %b %Y')
                    time_lbl.setText(f"{res['days_needed']} Days\nUntil {end_str}")
                    if 'schedule' in res:
                        for item in res['schedule']:
                            row = self.sched_table.rowCount()
                            self.sched_table.insertRow(row)
                            self.sched_table.setItem(row, 0, QTableWidgetItem(item['Date'].strftime("%d-%m")))
                            self.sched_table.setItem(row, 1, QTableWidgetItem(item['Day']))
                            self.sched_table.setItem(row, 2, QTableWidgetItem(item['Time']))
                            self.sched_table.setItem(row, 3, QTableWidgetItem(item['Subject']))
                else:
                    time_lbl.setText("Load Timetable")
        except Exception as e:
            QMessageBox.critical(self, "Calc Error", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())