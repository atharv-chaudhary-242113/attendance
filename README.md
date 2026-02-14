# Attendance Calculator & Forecaster

An advanced, Python-based analytical tool designed to track academic attendance, visualize absence patterns, and generate mathematically optimized recovery schedules. The system leverages machine learning to predict attendance risks and integrates directly with student timetables to provide actionable forecasts.

---

## **Key Features**

* **Visual Intelligence Dashboard:** * **Date Heatmap:** A visual calendar that uses predictive analytics to highlight high-risk days for absences.
* **Timetable Risk Matrix:** Identifies specific subject slots where attendance health is declining, colored by risk severity.


* **Machine Learning Integration:** Employs a **Random Forest Classifier** trained on historical absence data to predict the probability of missing future classes based on weekdays and months.
* **Dynamic Recovery Planner:** * Calculates the exact number of classes required to reach a target percentage (e.g., 75%).
* Generates a detailed **Recovery Schedule** showing the specific dates and subjects you must attend to meet your goals.


* **Operational Intelligence:**
* Automatically accounts for **Public Holidays** (2026 calendar) and weekend off-days (e.g., 3rd Saturdays).
* **CSV Data Pipeline:** Dedicated parsers for timetable exports and academic attendance summaries.


* **Modern Interface:** A high-contrast, dark-themed GUI built with **PyQt6** for professional-grade interaction.

---

## **Technology Stack**

* **Language:** Python 3.14+
* **GUI Framework:** PyQt6
* **Data Analysis:** Pandas, NumPy
* **Machine Learning:** Scikit-learn

---

## **Getting Started**

### **Installation**

1. Ensure you have Python installed.
2. Install dependencies:
```bash
pip install numpy pandas pyqt6 scikit-learn

```



### **Execution**

Run the entry-point script to launch the application:

```bash
python main.py

```

---

## **Project Structure**

* `main.py`: The system entry point that initializes the GUI.
* `backend/attendance_backend.py`: Contains `AttendanceBrain`, the core logic for parsing, ML training, and recovery calculation.
* `frontend/attendance_gui.py`: Defines the modern user interface, custom calendar widgets, and data visualization logic.
