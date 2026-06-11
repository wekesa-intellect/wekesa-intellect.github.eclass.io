import io
import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.http import HttpResponse
from django.utils import timezone

class ReportExporter:
    """Utility class for exporting reports to Excel and PDF"""
    
    @staticmethod
    def export_attendance_to_excel(course_data, course_code):
        """Export attendance data to Excel"""
        
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })
        
        cell_format = workbook.add_format({'border': 1, 'align': 'center'})
        warning_format = workbook.add_format({'bg_color': '#FFC107', 'border': 1, 'align': 'center'})
        danger_format = workbook.add_format({'bg_color': '#F44336', 'font_color': 'white', 'border': 1, 'align': 'center'})
        success_format = workbook.add_format({'bg_color': '#4CAF50', 'font_color': 'white', 'border': 1, 'align': 'center'})
        
        # Create summary worksheet
        summary_sheet = workbook.add_worksheet('Summary')
        summary_sheet.set_column('A:A', 25)
        summary_sheet.set_column('B:B', 20)
        
        # Add title
        summary_sheet.write('A1', f'Attendance Report - {course_code}', header_format)
        summary_sheet.write('A2', f'Generated on: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}', cell_format)
        
        # Add statistics
        row = 4
        summary_sheet.write(row, 0, 'Total Students:', header_format)
        summary_sheet.write(row, 1, course_data.get('total_students', 0), cell_format)
        row += 1
        summary_sheet.write(row, 0, 'Total Sessions:', header_format)
        summary_sheet.write(row, 1, course_data.get('total_sessions', 0), cell_format)
        row += 1
        summary_sheet.write(row, 0, 'Average Attendance:', header_format)
        summary_sheet.write(row, 1, f"{course_data.get('average_attendance', 0)}%", cell_format)
        row += 1
        summary_sheet.write(row, 0, 'Students Below 80%:', header_format)
        summary_sheet.write(row, 1, course_data.get('below_80_count', 0), danger_format if course_data.get('below_80_count', 0) > 0 else cell_format)
        
        # Create detailed attendance worksheet
        detail_sheet = workbook.add_worksheet('Detailed Attendance')
        detail_sheet.set_column('A:A', 20)
        detail_sheet.set_column('B:B', 25)
        detail_sheet.set_column('C:C', 15)
        detail_sheet.set_column('D:D', 15)
        detail_sheet.set_column('E:E', 15)
        detail_sheet.set_column('F:F', 20)
        
        # Headers
        headers = ['Student Name', 'Student Email', 'Attended Sessions', 'Total Sessions', 'Percentage', 'Status']
        for col, header in enumerate(headers):
            detail_sheet.write(0, col, header, header_format)
        
        # Write student data
        for row, student in enumerate(course_data.get('students', []), start=1):
            percentage = student.get('percentage', 0)
            
            # Choose format based on percentage
            if percentage >= 80:
                status_format = success_format
                status = 'Compliant'
            elif percentage >= 60:
                status_format = warning_format
                status = 'At Risk'
            else:
                status_format = danger_format
                status = 'Non-Compliant'
            
            detail_sheet.write(row, 0, student.get('name', ''), cell_format)
            detail_sheet.write(row, 1, student.get('email', ''), cell_format)
            detail_sheet.write(row, 2, student.get('attended', 0), cell_format)
            detail_sheet.write(row, 3, student.get('total', 0), cell_format)
            detail_sheet.write(row, 4, f"{percentage}%", cell_format)
            detail_sheet.write(row, 5, status, status_format)
        
        workbook.close()
        output.seek(0)
        
        # Create HTTP response
        filename = f"attendance_report_{course_code}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @staticmethod
    def export_attendance_to_pdf(course_data, course_code):
        """Export attendance data to PDF"""
        
        # Create PDF in memory
        buffer = io.BytesIO()
        
        # Create document with landscape orientation
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=72)
        
        # Story list for document elements
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2E7D32'),
            alignment=1,
            spaceAfter=30
        )
        
        # Add title
        story.append(Paragraph(f"Attendance Report - {course_code}", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Add metadata
        story.append(Paragraph(f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Summary table
        story.append(Paragraph("Summary Statistics", styles['Heading2']))
        summary_data = [
            ['Metric', 'Value'],
            ['Total Students', str(course_data.get('total_students', 0))],
            ['Total Sessions', str(course_data.get('total_sessions', 0))],
            ['Average Attendance', f"{course_data.get('average_attendance', 0)}%"],
            ['Students Below 80%', str(course_data.get('below_80_count', 0))],
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#4CAF50')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (1, 0), 12),
            ('GRID', (0, 0), (1, -1), 1, colors.black),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Student details table
        story.append(Paragraph("Student Attendance Details", styles['Heading2']))
        
        student_data = [['Student Name', 'Student Email', 'Attended', 'Total', 'Percentage', 'Status']]
        for student in course_data.get('students', []):
            percentage = student.get('percentage', 0)
            status = 'Compliant' if percentage >= 80 else 'Below 80%'
            student_data.append([
                student.get('name', ''),
                student.get('email', ''),
                str(student.get('attended', 0)),
                str(student.get('total', 0)),
                f"{percentage}%",
                status
            ])
        
        # Calculate column widths
        col_widths = [1.5*inch, 2*inch, 1*inch, 1*inch, 1.2*inch, 1.5*inch]
        student_table = Table(student_data, colWidths=col_widths, repeatRows=1)
        
        # Style the table
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2196F3')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
        
        # Add row colors
        for i in range(1, len(student_data)):
            if student_data[i][5] == 'Below 80%':
                table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#FFCDD2'))
            else:
                table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#C8E6C9'))
        
        student_table.setStyle(table_style)
        story.append(student_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Create HTTP response
        filename = f"attendance_report_{course_code}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response