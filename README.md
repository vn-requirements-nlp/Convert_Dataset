# Step 01: Tạo môi trường ảo (virtual environment) để cô lập thư viện
python -m venv .venv

# Step 02: Kích hoạt môi trường ảo (Windows PowerShell)
.\.venv\Scripts\Activate.ps1
# (Nếu bị chặn script: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)

# Step 03: Cài dependencies cho repo
pip install -r requirements.txt

# Step 04: Convert dataset Excel -> JSONL
python .\scripts\convert_excel_to_jsonl.py --in_xlsx .\data\Dataset_Full_EN.xlsx --sheet "Sheet1" --labelmap .\data\labelmap_from_excel.json --out_jsonl .\output\Dataset_Full_EN.jsonl

python .\scripts\convert_excel_to_jsonl.py --in_xlsx .\data\Dataset_Full_VI.xlsx --sheet "Sheet1" --labelmap .\data\labelmap_from_excel.json --out_jsonl .\output\Dataset_Full_VI.jsonl

