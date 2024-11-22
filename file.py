import pandas as pd
from category_mapping import apply_category_mapping

# 파일이 올바른 형식인지 확인
def allowed_file(filename,allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# 거래내역 data 파일 읽기
def read_transaction_file(file_path):
    try:
        file_extension = file_path.split('.')[-1].lower()
        if file_extension == 'xls':
            data = pd.read_excel(file_path, engine="xlrd")
        elif file_extension == 'xlsx':
            data = pd.read_excel(file_path, engine="openpyxl")
        else:
            raise ValueError("Unsupported file format. Please upload a .xls or .xlsx file.")
        return data
    except Exception as e:
        print(f"Error reading the file: {e}")
        return None