import csv
from io import StringIO

from django.http import HttpResponse


def safe_spreadsheet_value(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


class CSVExportService:
    @staticmethod
    def response(*, filename, headers, rows):
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([safe_spreadsheet_value(value) for value in row])
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class XLSXExportService:
    @staticmethod
    def build(*, sheet_name, headers, rows):
        from openpyxl import Workbook

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name
        worksheet.append([safe_spreadsheet_value(value) for value in headers])
        for row in rows:
            worksheet.append([safe_spreadsheet_value(value) for value in row])
        return workbook