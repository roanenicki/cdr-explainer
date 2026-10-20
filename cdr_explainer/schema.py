"""The CDR file format: column names, formats and tolerances."""

REQUIRED_COLUMNS = [
    "record_id",
    "calling_number",
    "called_number",
    "start_time",
    "end_time",
    "duration_sec",
]
OPTIONAL_COLUMNS = ["call_type", "cell_id"]
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
PHONE_PATTERN = r"^\+?\d{10,15}$"
INTEGER_PATTERN = r"^-?\d+$"
DURATION_TOLERANCE_SEC = 1
