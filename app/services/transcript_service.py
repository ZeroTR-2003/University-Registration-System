"""
Transcript Service
Handles generation of official PDF transcripts using ReportLab.
"""

from datetime import datetime
from io import BytesIO

from app.models.enrollment import Enrollment
from app.models.profile import StudentProfile
from app.models.course import Course, CourseSection


class TranscriptService:
    """Service for generating official academic transcripts."""
    
    @staticmethod
    def generate_transcript(student_profile: StudentProfile, official: bool = True) -> BytesIO:
        """
        Generate a PDF transcript for a student.
        
        Args:
            student_profile: StudentProfile instance
            official: Whether to mark as official transcript
            
        Returns:
            BytesIO buffer containing the PDF
        """
        # Lazy import ReportLab to avoid hard dependency at app startup
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            )
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        except Exception as e:
            raise RuntimeError("ReportLab is required to generate transcripts. Install 'reportlab' and try again.") from e

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build document elements
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#003366'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.black,
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#003366'),
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica'
        )
        
        # Header
        elements.append(Paragraph("UNIVERSITY REGISTRATION SYSTEM", title_style))
        elements.append(Paragraph("Official Academic Transcript" if official else "Unofficial Academic Transcript", subtitle_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Watermark for unofficial transcripts
        if not official:
            watermark_style = ParagraphStyle(
                'Watermark',
                parent=styles['Normal'],
                fontSize=16,
                textColor=colors.red,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            elements.append(Paragraph("*** UNOFFICIAL ***", watermark_style))
            elements.append(Spacer(1, 0.1*inch))
        
        # Student Information
        elements.append(Paragraph("STUDENT INFORMATION", header_style))
        
        student_data = [
            ["Name:", f"{student_profile.user.first_name} {student_profile.user.last_name}"],
            ["Student Number:", str(student_profile.student_number)],
            ["Date of Birth:", student_profile.user.birth_date.strftime('%B %d, %Y') if getattr(student_profile.user, 'birth_date', None) else "N/A"],
            ["Major:", student_profile.major or "Undeclared"],
            ["Academic Status:", student_profile.academic_status or "N/A"],
        ]
        
        student_table = Table(student_data, colWidths=[1.5*inch, 4*inch])
        student_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        elements.append(student_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Academic Summary
        elements.append(Paragraph("ACADEMIC SUMMARY", header_style))
        
        summary_data = [
            ["Cumulative GPA:", f"{student_profile.gpa:.2f}" if (student_profile.gpa is not None) else "N/A"],
            ["Total Credits Earned:", str(student_profile.total_credits_earned or 0)],
            ["Academic Status:", student_profile.academic_status or "Good Standing"],
        ]
        
        summary_table = Table(summary_data, colWidths=[1.5*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Course History by Term
        elements.append(Paragraph("COURSE HISTORY", header_style))
        
        # Get all enrollments (graded and ungraded), grouped by term
        enrollments = (
            Enrollment.query
            .filter_by(student_id=student_profile.id)
            .join(CourseSection)
            .order_by(CourseSection.start_date.desc())
            .all()
        )
        
        # Group by term label (string) and capture representative dates
        terms_dict = {}
        for enrollment in enrollments:
            section = enrollment.course_section
            term_label = section.term
            if term_label not in terms_dict:
                terms_dict[term_label] = {
                    'term_label': term_label,
                    'start_date': section.start_date,
                    'end_date': section.end_date,
                    'enrollments': []
                }
            terms_dict[term_label]['enrollments'].append(enrollment)
        
        # Sort terms by start date (newest first for transcript)
        sorted_terms = sorted(
            terms_dict.values(),
            key=lambda x: (x['start_date'] or datetime.min.date()),
            reverse=True
        )
        
        for term_data in sorted_terms:
            term_label = term_data['term_label']
            term_enrollments = term_data['enrollments']
            start_date = term_data['start_date']
            end_date = term_data['end_date']
            
            # Term header
            if start_date and end_date:
                term_title = f"{term_label} ({start_date.strftime('%B %Y')} - {end_date.strftime('%B %Y')})"
            else:
                term_title = term_label
            term_style = ParagraphStyle(
                'TermStyle',
                parent=styles['Normal'],
                fontSize=11,
                fontName='Helvetica-Bold',
                spaceBefore=12,
                spaceAfter=6
            )
            elements.append(Paragraph(term_title, term_style))
            
            # Course table
            course_data = [
                ["Course", "Title", "Credits", "Grade", "Points"]
            ]
            
            term_credits = 0
            term_points = 0
            
            for enrollment in term_enrollments:
                course = enrollment.course_section.course
                credits = course.credits
                grade = enrollment.grade
                grade_points = enrollment.grade_points
                
                # Display "Unavailable" for missing grades
                display_grade = grade if grade else "Unavailable"
                display_points = (grade_points * credits) if (grade_points is not None) else 0
                
                course_data.append([
                    course.code,
                    course.title[:35] + "..." if len(course.title) > 35 else course.title,
                    str(credits),
                    display_grade,
                    f"{display_points:.2f}"
                ])
                
                term_credits += credits
                term_points += (grade_points * credits) if (grade_points is not None) else 0
            
            # Term totals
            term_gpa = (term_points / term_credits) if term_credits > 0 else 0
            course_data.append([
                "Term Totals:",
                "",
                str(term_credits),
                f"GPA: {term_gpa:.2f}",
                f"{term_points:.2f}"
            ])
            
            course_table = Table(
                course_data,
                colWidths=[1.2*inch, 2.8*inch, 0.7*inch, 0.6*inch, 0.7*inch]
            )
            
            course_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                
                # Data rows
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -2), 9),
                ('ALIGN', (2, 1), (-1, -2), 'CENTER'),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                
                # Totals row
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 9),
                ('ALIGN', (2, -1), (-1, -1), 'CENTER'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8E8E8')),
                ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.black),
                
                # General
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            elements.append(course_table)
            elements.append(Spacer(1, 0.15*inch))
        
        # Grading Scale
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("GRADING SCALE", header_style))
        
        grade_scale_data = [
            ["A = 4.0", "A- = 3.7", "B+ = 3.3", "B = 3.0"],
            ["B- = 2.7", "C+ = 2.3", "C = 2.0", "C- = 1.7"],
            ["D+ = 1.3", "D = 1.0", "F = 0.0", ""]
        ]
        
        grade_scale_table = Table(grade_scale_data, colWidths=[1.4*inch, 1.4*inch, 1.4*inch, 1.4*inch])
        grade_scale_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        elements.append(grade_scale_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Footer
        if official:
            footer_text = f"This is an official transcript issued on {datetime.now().strftime('%B %d, %Y')}."
        else:
            footer_text = f"This is an unofficial transcript generated on {datetime.now().strftime('%B %d, %Y')}. For official transcripts, please contact the Registrar's Office."
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        )
        
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph(footer_text, footer_style))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def generate_filename(student_profile: StudentProfile, official: bool = True) -> str:
        """
        Generate a standardized filename for the transcript.
        
        Args:
            student_profile: StudentProfile instance
            official: Whether this is an official transcript
            
        Returns:
            Filename string
        """
        transcript_type = "official" if official else "unofficial"
        timestamp = datetime.now().strftime('%Y%m%d')
        last_name = student_profile.user.last_name.replace(' ', '_')
        student_id = student_profile.student_number
        
        return f"transcript_{transcript_type}_{last_name}_{student_id}_{timestamp}.pdf"
