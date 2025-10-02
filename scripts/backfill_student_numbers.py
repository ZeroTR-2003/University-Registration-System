#!/usr/bin/env python3
"""
Backfill student_number for StudentProfile records where it is missing or empty.
Uses per-year sequential format YYYY<N>. Existing non-empty values are preserved.

Usage:
  python scripts/backfill_student_numbers.py
"""
from app import create_app, db
from app.models.profile import StudentProfile
from app.services.identifiers import generate_student_number


def main():
    app = create_app('development')
    with app.app_context():
        updated = 0
        students = StudentProfile.query.all()
        for s in students:
            if not s.student_number or str(s.student_number).strip() == '':
                s.student_number = generate_student_number(s.enrollment_year or None)
                updated += 1
        if updated:
            db.session.commit()
        print(f"Backfill complete. Updated {updated} student numbers.")


if __name__ == '__main__':
    main()
