from io import BytesIO
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def generate_standard_excel_template() -> BytesIO:
    """
    Generates a professionally styled standard Excel template (.xlsx)
    pre-formatted with columns:
      - Trainee_Name | اسم المتدرب
      - Training_Date | تاريخ التدريب
      - Custom_Text | نص إضافي
    Styled with CertFlow Studio brand colors (Primary Deep Navy #004B87).
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "بيانات المتدربين"
    
    # Enable RTL for natural Arabic reading
    ws.views.sheetView[0].rightToLeft = True

    headers = [
        "Trainee_Name",
        "Training_Date",
        "Custom_Text"
    ]
    ws.append(headers)

    # Styling definitions
    navy_fill = PatternFill(start_color="004B87", end_color="004B87", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_text = Alignment(horizontal="right", vertical="center")
    
    thin_border_side = Side(border_style="thin", color="D1D5DB")
    cell_border = Border(
        top=thin_border_side,
        bottom=thin_border_side,
        left=thin_border_side,
        right=thin_border_side
    )

    # Style header row
    ws.row_dimensions[1].height = 34
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = navy_fill
        cell.font = header_font
        cell.alignment = align_center
        cell.border = cell_border

    # Sample demo rows to guide the user
    sample_rows = [
        ("سارة محمد المنصور", "2026-10-25", "تقدير ممتاز | With Distinction"),
        ("خالد عبدالله العتيبي", "2026-10-25", "اجتياز متقدم | Advanced Level"),
        ("Reem Faisal Al-Harbi", "2026-10-26", "إتمام مسار التصميم الطباعي"),
        ("أحمد إبراهيم الشمري", "2026-10-26", "تقدير جيد جداً"),
        ("Noura Saleh Al-Ghamdi", "2026-10-27", "مرتبة الشرف الأولى")
    ]

    data_font = Font(name="Arial", size=10, color="1E293B")
    alt_fill = PatternFill(start_color="F4F7FA", end_color="F4F7FA", fill_type="solid")

    for row_idx, row_data in enumerate(sample_rows, start=2):
        ws.append(row_data)
        ws.row_dimensions[row_idx].height = 24
        is_even = (row_idx % 2 == 0)
        for col_idx in range(1, len(row_data) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = cell_border
            if col_idx == 2:
                cell.alignment = align_center
            else:
                cell.alignment = align_text
            if is_even:
                cell.fill = alt_fill

    # Set column widths
    column_widths = [34, 24, 34]
    for i, width in enumerate(column_widths, start=1):
        col_letter = get_column_letter(i)
        ws.column_dimensions[col_letter].width = width

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

