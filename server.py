from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
import shutil, uuid, os
from urllib.parse import quote
from Core import analyze, fix

app = FastAPI()

UPLOAD = "uploads"
OUTPUT = "outputs"
os.makedirs(UPLOAD, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)

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





CURRENT = "current.pdf"

@app.post("/upload")
def upload_api(file: UploadFile = File(None)):
    if not file or file.filename == "":
        return RedirectResponse("/", 302)

    tmp = CURRENT + ".tmp"
    with open(tmp, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 確保寫入完成後再覆蓋 current
    if os.path.getsize(tmp) > 0:
        os.replace(tmp, CURRENT)

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
