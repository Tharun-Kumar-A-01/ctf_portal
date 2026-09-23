import csv
import io
import openpyxl

def parse_csv_stream(file_stream, max_rows=1000):
    """
    Parses a CSV file stream or string using Python standard library `csv`.
    Returns dict containing headers, rows (list of dicts), and total row count.
    """
    content = file_stream.read()
    if isinstance(content, bytes):
        content = content.decode('utf-8', errors='replace')
    
    stream = io.StringIO(content)
    reader = csv.DictReader(stream, skipinitialspace=True)
    
    headers = reader.fieldnames or []
    rows = []
    
    for i, row in enumerate(reader):
        if i >= max_rows:
            break
        rows.append(row)
        
    return {
        'headers': headers,
        'rows': rows,
        'total_rows': len(rows)
    }

def parse_excel_stream(file_stream, sheet_name=None, max_rows=1000):
    """
    Parses an Excel (.xlsx / .xlsm) file stream using `openpyxl`.
    Returns dict containing sheet list, selected sheet data with headers and rows.
    """
    workbook = openpyxl.load_workbook(file_stream, data_only=True)
    sheets = workbook.sheetnames
    
    target_sheet = sheet_name if sheet_name in sheets else sheets[0]
    sheet = workbook[target_sheet]
    
    data = []
    for row in sheet.iter_rows(values_only=True):
        if any(cell is not None for cell in row):
            data.append([str(cell) if cell is not None else "" for cell in row])
            
    if not data:
        return {'headers': [], 'rows': [], 'sheets': sheets, 'sheet_name': target_sheet, 'total_rows': 0}
        
    headers = data[0]
    rows_data = data[1:max_rows+1]
    
    rows_as_dicts = []
    for row in rows_data:
        row_dict = {}
        for h, cell in zip(headers, row):
            if h:
                row_dict[h] = cell
        rows_as_dicts.append(row_dict)

    return {
        'headers': headers,
        'rows': rows_as_dicts,
        'sheets': sheets,
        'sheet_name': target_sheet,
        'total_rows': len(rows_as_dicts)
    }
