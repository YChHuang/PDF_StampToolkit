from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
import shutil, uuid, os
from urllib.parse import quote
from core import analyze, fix

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
TMP_DIR  = os.path.join(DATA_DIR, "tmp")
UPLOAD   = os.path.join(BASE_DIR, "uploads")
OUTPUT   = os.path.join(BASE_DIR, "outputs")

os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(UPLOAD, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)

CURRENT = os.path.join(DATA_DIR, "current.pdf")



@app.get("/")
def home(result: str = ""):
    return HTMLResponse(f"""
    <html>
        <body>
            <h2>PDF Geometry Fix Tool</h2>

            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file">
                <button type="submit">Upload PDF</button>
            </form>
            <hr>

            <form action="/analyze" method="post">
                <button type="submit">Analyze</button>
            </form>

            <form action="/fix" method="post">
                <button type="submit">Fix PDF</button>
            </form>

            <pre>{result}</pre>
        </body>
    </html>
    """)





@app.post("/upload")
def upload_api(file: UploadFile = File(None)):
    if not file or file.filename == "":
        return RedirectResponse("/", 302)

    tmp_path = os.path.join(TMP_DIR, str(uuid.uuid4()) + ".pdf")

    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 確保寫入完成後再覆蓋 current
    if os.path.getsize(tmp_path) > 0:
        os.replace(tmp_path, CURRENT)

    return RedirectResponse("/", 302)



@app.post("/analyze")
def analyze_api():
    if not os.path.exists(CURRENT) or os.path.getsize(CURRENT) == 0:
        return RedirectResponse("/?result=No+valid+PDF+loaded", 302)

    result = analyze(CURRENT)
    return RedirectResponse("/?result=" + quote(result), 302)


@app.post("/fix")
def fix_api():
    if not os.path.exists(CURRENT) or os.path.getsize(CURRENT) == 0:
        return RedirectResponse("/?result=No+valid+PDF+loaded", 302)

    out_path = os.path.join(OUTPUT, str(uuid.uuid4()) + ".pdf")
    fix(CURRENT, out_path)
    return FileResponse(out_path, filename="fixed.pdf")
