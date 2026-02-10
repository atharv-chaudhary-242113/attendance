import pandas as pd
import numpy as np
from datetime import timedelta, date
import math
import re
from sklearn.ensemble import RandomForestClassifier


class AttendanceBrain:
    def __init__(self):
        self.model_daily = RandomForestClassifier(n_estimators=100, random_state=42)
        self.timetable = {}  # {0: {'08:45': 'Social Psych'}, ...}
        self.full_history = []
        self.subject_map = {}  # Maps "BPSY201-4" -> "SOCIAL PSYCHOLOGY"
        self.is_trained = False

        self.auto_total = 0
        self.auto_absent = 0
        self.has_summary_data = False

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
            "Mid-sems 4th 1": date(2026, 2, 14),
            "Mid-sems 4th 2": date(2026, 2, 15),
            "Mid-sems 4th 3": date(2026, 2, 16),
            "Mid-sems 4th 4": date(2026, 2, 17),
            "Mid-sems 4th 5": date(2026, 2, 18),
            "Mid-sems 4th 6": date(2026, 2, 19),
            "Mid-sems 4th 7": date(2026, 2, 20),
        }
        self.sem_config = {'even_end': (5, 31), 'odd_end': (12, 15)}

    def get_semester_end_date(self, start_date):
        year, month = start_date.year, start_date.month
        if 1 <= month <= 6:
            end = date(year, self.sem_config['even_end'][0], self.sem_config['even_end'][1])
            return start_date + timedelta(days=180) if start_date > end else end
        else:
            end = date(year, self.sem_config['odd_end'][0], self.sem_config['odd_end'][1])
            return date(year + 1, 5, 31) if start_date > end else end

    def is_holiday_or_off(self, date_obj):
        if date_obj.weekday() == 6: return True
        if date_obj.weekday() == 5 and 15 <= date_obj.day <= 21: return True
        return date_obj in self.public_holidays.values()

    def clean_subject_name(self, raw_text):
        """
        Extracts clean name from "SUBJECT NAME CODE".
        Example: "SOCIAL PSYCHOLOGY BPSY201-4" -> "SOCIAL PSYCHOLOGY"
        """
        raw_text = str(raw_text).strip()

        # 1. If we already mapped this code/text to a clean name, use it
        if raw_text in self.subject_map:
            return self.subject_map[raw_text]

        # 2. Heuristic: Split by known separators or regex
        # Look for the pattern: (Name) (Code with numbers/dashes at end)
        match = re.search(r'^(.*?)\s+([A-Z0-9-]{3,})$', raw_text)
        if match:
            name_part = match.group(1).strip()
            code_part = match.group(2).strip()
            # If name part is substantial, map code -> name
            if len(name_part) > 2:
                self.subject_map[code_part] = name_part
                self.subject_map[raw_text] = name_part
                return name_part

        return raw_text

    def parse_timetable(self, file_path):
        self.timetable = {}
        try:
            df = pd.read_csv(file_path, header=None, dtype=str).fillna("")
            days_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5}
            col_to_time = {}

            # 1. Map Time Columns
            for idx, row in df.iterrows():
                row_times = {}
                for col_idx, val in enumerate(row.values):
                    val_str = str(val).strip()
                    match = re.search(r'(\d{1,2}:\d{2})', val_str)
                    if match:
                        # Normalize to HH:MM format
                        h, m = match.group(1).split(':')
                        clean_time = f"{int(h):02d}:{m}"
                        row_times[col_idx] = clean_time
                if len(row_times) >= 3:
                    col_to_time = row_times
                    break

            if not col_to_time: return False, "Could not detect time slots."

            # 2. Extract and Clean Subjects
            for idx, row in df.iterrows():
                row_vals = [str(x).strip().lower() for x in row.values]
                if not row_vals: continue
                first_col = re.sub(r'[^\w]', '', row_vals[0])

                if first_col in days_map:
                    current_day = days_map[first_col]
                    if current_day not in self.timetable: self.timetable[current_day] = {}

                    for col_idx, time_str in col_to_time.items():
                        if col_idx < len(row):
                            raw_subject = str(row[col_idx]).strip()
                            bad = ['nan', '', 'break', 'lunch', 'mentoring', 'session', 'course code', 'time']
                            if len(raw_subject) > 2 and not any(k == raw_subject.lower() for k in bad):
                                # CLEAN THE NAME HERE
                                clean_name = self.clean_subject_name(raw_subject)
                                self.timetable[current_day][time_str] = clean_name

            return True, f"Parsed {sum(len(v) for v in self.timetable.values())} classes."
        except Exception as e:
            return False, f"Error: {e}"

    def parse_attendance_summary(self, file_path):
        """ Learns Subject Names from Summary and gets Totals """
        try:
            df = pd.read_csv(file_path)
            # Normalize headers
            df.columns = [c.strip() for c in df.columns]

            # 1. Learn Names (Map Code/Name if possible)
            # If summary has "Subject Name", assume it is the source of truth
            col_sub = next((c for c in df.columns if 'Subject' in c), None)
            if col_sub:
                for val in df[col_sub].dropna():
                    clean = str(val).strip()
                    # Add to map so fuzzy match works later
                    self.subject_map[clean] = clean

            # 2. Get Totals
            df_no_header = pd.read_csv(file_path, header=None)
            for idx, row in df_no_header.iterrows():
                row_str = " ".join([str(x).lower() for x in row.values[:3]])
                if "total" in row_str and "percentage" not in row_str:
                    nums = []
                    for val in row.values:
                        try:
                            v = float(str(val).replace('%', '').strip())
                            if not np.isnan(v): nums.append(int(v))
                        except:
                            pass
                    if len(nums) >= 3:
                        self.auto_total = nums[-3]
                        self.auto_absent = nums[-1]
                        if self.auto_total < self.auto_absent:
                            self.auto_total = nums[-1]
                            self.auto_absent = nums[-3]
                        self.has_summary_data = True
                        break
            return True, f"Auto: {self.auto_total} Total, {self.auto_absent} Absent"
        except Exception as e:
            return False, str(e)

    def load_absence_details(self, file_path):
        try:
            abs_df = pd.read_csv(file_path)
            abs_df['Date'] = pd.to_datetime(abs_df['Date'], dayfirst=True, errors='coerce').dt.date
            abs_df = abs_df.dropna(subset=['Date'])
            if abs_df.empty: return False, "No valid dates."

            self.full_history = []
            col_total = next((c for c in abs_df.columns if 'Total' in c), None)

            # Identify Time Columns (P8-45AM etc)
            time_cols = [c for c in abs_df.columns if "P" in c and c not in ['Total', 'Percentage']]

            for idx, row in abs_df.iterrows():
                d = row['Date']
                if self.is_holiday_or_off(d): continue

                is_absent_day = 0
                if col_total:
                    val = pd.to_numeric(row[col_total], errors='coerce')
                    if val > 0: is_absent_day = 1

                for col in time_cols:
                    val = str(row[col]).strip()
                    if val and val.lower() != 'nan':
                        # Infer time string for heatmap matching
                        time_guess = "Unknown"
                        match = re.search(r'(\d{1,2})[-:](\d{2})', col)
                        if match:
                            h, m = match.groups()
                            time_guess = f"{int(h):02d}:{m}"

                        # Use Clean Name
                        clean_name = self.clean_subject_name(val)

                        self.full_history.append({
                            'Date': d, 'Day': d.weekday(),
                            'Subject': clean_name,
                            'Time': time_guess,
                            'IsAbsent': 1
                        })
                        is_absent_day = 1

                self.full_history.append({'Date': d, 'Subject': 'Daily_Aggregate', 'IsAbsent': is_absent_day})

            self.train_models()
            return True, "Absence Details Loaded."
        except Exception as e:
            return False, str(e)

    def train_models(self):
        if not self.full_history: return
        data = [x for x in self.full_history if x['Subject'] == 'Daily_Aggregate']
        if not data: return
        df = pd.DataFrame(data)
        X = [[r['Date'].weekday(), r['Date'].day, r['Date'].month] for _, r in df.iterrows()]
        y = df['IsAbsent'].tolist()
        if len(X) > 5:
            self.model_daily.fit(X, y)
            self.is_trained = True

    def predict_day_risk(self, date_obj):
        if not self.is_trained or self.is_holiday_or_off(date_obj): return 0.0
        try:
            return self.model_daily.predict_proba([[date_obj.weekday(), date_obj.day, date_obj.month]])[0][1]
        except:
            return 0.0

    def get_subject_risks(self):
        # Return cleaned names
        subjects = [x['Subject'] for x in self.full_history if x['Subject'] != 'Daily_Aggregate']
        if not subjects: return []
        from collections import Counter
        counts = Counter(subjects)
        most_absent = counts.most_common(1)[0][1] if counts else 1
        return [(subj, count / most_absent) for subj, count in counts.most_common(10)]

    def get_slot_risk_matrix(self):
        """
        Calculates absence risk for every (Day, Time) slot.
        Returns: {(0, '08:45'): 0.8, ...}
        """
        # Filter for actual class absences
        class_hist = [x for x in self.full_history if x['Subject'] != 'Daily_Aggregate']

        slot_counts = {}
        for item in class_hist:
            key = (item['Day'], item['Time'])
            slot_counts[key] = slot_counts.get(key, 0) + 1

        if not slot_counts: return {}

        # Normalize relative to the worst slot
        max_abs = max(slot_counts.values())
        return {k: v / max_abs for k, v in slot_counts.items()}

    def calculate_recovery_plan(self, target_percent, manual_total, manual_absent, start_date, limit_date):
        if manual_total < 0: manual_total = 0
        if manual_absent < 0: manual_absent = 0

        present = manual_total - manual_absent
        if manual_total == 0:
            current_pct = 0.0
        else:
            current_pct = (present / manual_total) * 100

        result = {
            "current_pct": current_pct, "target": target_percent,
            "status": "safe", "classes_skippable": 0, "classes_needed": 0, "days_needed": 0,
            "end_date": start_date
        }

        if target_percent >= 100 and manual_absent > 0:
            result["status"] = "impossible"
            return result

        if current_pct < target_percent:
            t = target_percent / 100.0
            numerator = (t * manual_total) - present
            denominator = 1 - t
            if denominator <= 0:
                result["status"] = "impossible"
                return result

            needed = math.ceil(numerator / denominator)
            result["classes_needed"] = needed

            if self.timetable:
                schedule = self.get_recovery_schedule(needed, start_date, limit_date)
                if not schedule:
                    result["status"] = "no_classes_found"
                    result["end_date"] = start_date
                else:
                    result["days_needed"] = len(set(x['Date'] for x in schedule))
                    result["end_date"] = schedule[-1]['Date']
                    result["schedule"] = schedule

                    if len(schedule) < needed:
                        result["status"] = "impossible_timeframe"
                        ft = manual_total + len(schedule)
                        fp = present + len(schedule)
                        result["max_possible"] = (fp / ft) * 100
                    else:
                        result["status"] = "deficit"
            else:
                result["status"] = "deficit"
        else:
            t = target_percent / 100.0
            if t == 0:
                skippable = 9999
            else:
                skippable = math.floor((present / t) - manual_total)
            result["status"] = "surplus"
            result["classes_skippable"] = skippable

        return result

    def get_recovery_schedule(self, classes_needed, start_date, limit_date):
        schedule = []
        sim_date = start_date
        classes_count = 0
        while classes_count < classes_needed and sim_date <= limit_date:
            if not self.is_holiday_or_off(sim_date):
                day_idx = sim_date.weekday()
                if day_idx in self.timetable:
                    daily_classes = self.timetable[day_idx]
                    sorted_times = sorted(daily_classes.keys())
                    for time_str in sorted_times:
                        if classes_count < classes_needed:
                            schedule.append({
                                "Date": sim_date, "Day": sim_date.strftime("%A"),
                                "Time": time_str, "Subject": daily_classes[time_str]
                            })
                            classes_count += 1
            sim_date += timedelta(days=1)
        return schedule