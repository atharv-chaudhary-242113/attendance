import pandas as pd
import numpy as np
from datetime import timedelta, date, datetime
from sklearn.ensemble import RandomForestClassifier


class AttendanceBrain:
    def __init__(self):
        self.model_daily = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model_subject = {}
        self.timetable = {}
        self.full_history = []
        self.is_trained = False

        # Holiday Dictionary (Ready for Trip Planner)
        self.public_holidays = {
            "Hazrat Ali Jayanti": date(2026, 1, 3),
            "Republic Day": date(2026, 1, 26),
            "Maha Shivaratri": date(2026, 2, 15),
            "Holika Dahan": date(2026, 3, 2),
            "Holi": date(2026, 3, 4),
            "Id Ul-Fitr": date(2026, 3, 21),
            "Ram Navami": date(2026, 3, 26),
            "Mahavir Jayanti": date(2026, 3, 31),
            "Good Friday": date(2026, 4, 3),
            "Dr. B.R. Ambedkar Jayanti": date(2026, 4, 14),
            "Buddha Purnima": date(2026, 5, 1),
            "Bakrid/Eid-Ul-Zuha": date(2026, 5, 27),
            "Muharram": date(2026, 6, 26),
            "Independence Day": date(2026, 8, 15),
            "Eid-E-Milad/Barawafat": date(2026, 8, 26),
            "Raksha Bandhan": date(2026, 8, 28),
            "Janmashatami": date(2026, 9, 4),
            "Mahatam Gandhi Jayanti": date(2026, 10, 2),
            "Dusshera (Maha Ashtami)": date(2026, 10, 19),
            "Dushera (Maha Navami)/Vijaydashami": date(2026, 10, 20),
            "Deepawali": date(2026, 11, 8),
            "Govardhan Pooja": date(2026, 11, 9),
            "Bhai Dooj / Chitragupta Jayanti": date(2026, 11, 11),
            "Guru Nanak Jayanti / Kartik Purnima": date(2026, 11, 24),
            "Christmas Day": date(2026, 12, 25),
        }

        # Standard time slots (Aligned with your CSV headers)
        self.time_slots = [
            "08:45", "09:45", "10:45", "11:45",
            "12:45", "13:45", "14:45", "15:45", "16:45"
        ]

        # Mapping Absence CSV headers to standard time slots
        self.header_map = {
            "P8-45AM": "08:45", "P9-45AM": "09:45", "P10-45AM": "10:45",
            "P11-45AM": "11:45", "P12-45PM": "12:45", "P13-45PM": "13:45",
            "P14-45PM": "14:45", "P15-45PM": "15:45", "P16-45PM": "16:45"
        }

    def is_holiday_or_off(self, date_obj):
        # 1. Sunday
        if date_obj.weekday() == 6:
            return True

        # 2. Third Saturday (Date 15-21)
        if date_obj.weekday() == 5 and 15 <= date_obj.day <= 21:
            return True

        # 3. Public Holidays (Check against Dictionary Values)
        return date_obj in self.public_holidays.values()

    def parse_timetable(self, file_path):
        """
        Parses the multi-line timetable CSV robustly.
        """
        try:
            # Read as strings to handle messy formatting
            df = pd.read_csv(file_path, header=None, dtype=str)

            days_map = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5}
            current_day = None

            for index, row in df.iterrows():
                # Clean the first column
                first_col = str(row[0]).strip() if pd.notna(row[0]) else ""

                # Detect Day Block
                if first_col in days_map:
                    current_day = days_map[first_col]

                # Check if this row contains subjects
                # We look for rows where the second column is "Course Code" or similar structure
                # OR we look for the row containing the subject codes directly if they align with the day
                sec_col = str(row[1]).strip() if len(row) > 1 and pd.notna(row[1]) else ""

                if sec_col == "Course Name" and current_day is not None:
                    # Map columns to time slots
                    for i, time_slot in enumerate(self.time_slots):
                        col_idx = i + 2  # Start from column 2

                        # CRITICAL FIX: Check if column exists before access
                        if col_idx < len(row):
                            subject = str(row[col_idx]).strip()
                            # Filter out empty, breaks, or NaNs
                            if subject and subject.lower() not in ['nan', '', 'break', 'lunch', 'breakfast break']:
                                if current_day not in self.timetable:
                                    self.timetable[current_day] = {}
                                self.timetable[current_day][time_slot] = subject

            return True, "Timetable Parsed"
        except Exception as e:
            return False, f"Timetable Error: {e}"

    def load_data(self, absence_path, timetable_path):
        # 1. Parse Timetable
        success, msg = self.parse_timetable(timetable_path)
        if not success: return False, msg

        # 2. Parse Absence File
        try:
            abs_df = pd.read_csv(absence_path)
            # Safe date parsing
            abs_df['Date'] = pd.to_datetime(abs_df['Date'], dayfirst=True, errors='coerce').dt.date
            abs_df = abs_df.dropna(subset=['Date'])  # Drop rows where date failed to parse

            if abs_df.empty:
                return False, "Absence file contains no valid dates."

            # 3. Generate Full History
            min_date = abs_df['Date'].min()
            max_date = abs_df['Date'].max()
            current = min_date

            self.full_history = []

            while current <= max_date:
                if not self.is_holiday_or_off(current):
                    day_idx = current.weekday()

                    if day_idx in self.timetable:
                        daily_schedule = self.timetable[day_idx]
                        day_record = abs_df[abs_df['Date'] == current]

                        for time_slot, subject in daily_schedule.items():
                            was_absent = 0

                            if not day_record.empty:
                                col_name = next((k for k, v in self.header_map.items() if v == time_slot), None)

                                if col_name and col_name in abs_df.columns:
                                    val = day_record.iloc[0][col_name]
                                    # If cell has text (Subject Name), it's an absence.
                                    if pd.notna(val) and str(val).strip() != "":
                                        was_absent = 1

                            self.full_history.append({
                                'Date': current,
                                'DayOfWeek': day_idx,
                                'TimeSlot': time_slot,
                                'Subject': subject,
                                'IsAbsent': was_absent
                            })

                current += timedelta(days=1)

            self.train_models()
            return True, f"Success. Processed {len(self.full_history)} classes."

        except Exception as e:
            return False, f"Absence File Error: {e}"

    def train_models(self):
        if not self.full_history: return

        df = pd.DataFrame(self.full_history)

        # Subject Risk
        sub_stats = df.groupby('Subject')['IsAbsent'].mean()
        self.model_subject = sub_stats.to_dict()

        # Daily Risk Model
        daily_df = df.groupby('Date').agg({
            'IsAbsent': 'max',  # 1 if any class skipped
            'DayOfWeek': 'first'
        }).reset_index()

        X = []
        y = []
        for _, row in daily_df.iterrows():
            d = row['Date']
            features = [d.weekday(), d.day, d.month]
            X.append(features)
            y.append(row['IsAbsent'])

        if len(X) > 5:
            self.model_daily.fit(X, y)
            self.is_trained = True

    def predict_day_risk(self, date_obj):
        if not self.is_trained or self.is_holiday_or_off(date_obj):
            return 0.0
        try:
            return self.model_daily.predict_proba([[date_obj.weekday(), date_obj.day, date_obj.month]])[0][1]
        except:
            return 0.0

    def get_subject_risk(self):
        return sorted(self.model_subject.items(), key=lambda x: x[1], reverse=True)

    def get_hourly_risk(self):
        df = pd.DataFrame(self.full_history)
        if df.empty: return []
        hourly = df.groupby('TimeSlot')['IsAbsent'].mean().to_dict()
        return sorted(hourly.items())