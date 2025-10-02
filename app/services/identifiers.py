"""Identifier generation utilities (student numbers, etc.)."""
from datetime import datetime
from app.models import db
from app.models.profile import StudentProfile


def generate_student_number(year: int | None = None) -> str:
    """
    Generate a unique student number of the form <YYYY><N>,
    where YYYY is the current year and N is a sequential integer per year starting at 1.
    Existing student numbers with other formats (e.g., 'SYYYYxxxxx') are preserved and ignored.
    """
    if year is None:
        year = datetime.now().year
    prefix = str(year)

    # Count existing student numbers starting with this year's prefix and extract max sequence
    existing = db.session.query(StudentProfile.student_number).filter(
        StudentProfile.student_number.like(f"{prefix}%")
    ).all()

    max_seq = 0
    for (sn,) in existing:
        try:
            tail = sn.replace(prefix, '', 1)
            # Only consider purely numeric tails to avoid mixing formats
            if tail.isdigit():
                max_seq = max(max_seq, int(tail))
        except Exception:
            continue

    next_seq = max_seq + 1
    return f"{prefix}{next_seq}"
