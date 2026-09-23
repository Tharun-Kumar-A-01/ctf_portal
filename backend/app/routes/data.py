from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.utils.decorators import admin_required
from app.models import db, DataImport
from app.utils.parser_helper import parse_csv_stream, parse_excel_stream

data_bp = Blueprint('data', __name__, url_prefix='/api/data')

@data_bp.route('/upload', methods=['POST'])
@admin_required()
def upload_data():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'Empty filename'}), 400
        
    filename = file.filename.lower()
    
    current_user = get_jwt_identity()
    user_id = int(current_user) if current_user else None

    if filename.endswith('.csv'):
        parsed = parse_csv_stream(file.stream)
        file_type = 'csv'
    elif filename.endswith(('.xlsx', '.xls')):
        sheet_name = request.form.get('sheet')
        if sheet_name is not None and not isinstance(sheet_name, str):
            return jsonify({'error': 'sheet must be a string'}), 400
        parsed = parse_excel_stream(file.stream, sheet_name=sheet_name)
        file_type = 'xlsx'
    else:
        return jsonify({'error': 'Unsupported file format. Please upload a .csv or .xlsx file'}), 400

    import_record = DataImport(
        filename=file.filename,
        file_type=file_type,
        row_count=parsed.get('total_rows', 0),
        uploaded_by=user_id,
        status='completed'
    )
    
    db.session.add(import_record)
    db.session.commit()

    return jsonify({
        'message': f'Successfully parsed {file_type.upper()} file',
        'record': import_record.to_dict(),
        'parsed_data': parsed
    }), 200

@data_bp.route('/history', methods=['GET'])
@admin_required()
def get_history():
    imports = DataImport.query.order_by(DataImport.created_at.desc()).limit(20).all()
    return jsonify({
        'history': [imp.to_dict() for imp in imports]
    }), 200
