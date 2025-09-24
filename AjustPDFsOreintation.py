import os
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import (
    RectangleObject, NameObject, NumberObject,
    DecodedStreamObject, DictionaryObject
)

# ---- geometry helpers ----
def apply_matrix_to_point(x, y, a, b, c, d, e, f):
    return a*x + c*y + e, b*x + d*y + f

def transform_rect(rect, matrix):
    a,b,c,d,e,f = matrix
    x0,y0,x1,y1 = rect
    pts = [
        apply_matrix_to_point(x0,y0,a,b,c,d,e,f),
        apply_matrix_to_point(x0,y1,a,b,c,d,e,f),
        apply_matrix_to_point(x1,y0,a,b,c,d,e,f),
        apply_matrix_to_point(x1,y1,a,b,c,d,e,f),
    ]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return [min(xs), min(ys), max(xs), max(ys)]

def invert_affine(mat):
    """Invert affine 6-tuple (a,b,c,d,e,f) respecting PDF coordinate mapping."""
    a,b,c,d,e,f = mat
    det = a*d - b*c
    if abs(det) < 1e-12:
        # 非常少見：不可逆；回傳單位避免崩潰
        return (1.0,0.0,0.0,1.0,0.0,0.0)
    ia =  d / det
    ib = -b / det
    ic = -c / det
    id =  a / det
    # 逆平移 = -A^{-1} * t
    ie = -(ia*e + ic*f)
    if_ = -(ib*e + id*f)
    return (ia, ib, ic, id, ie, if_)

# ---- stream wrapping ----
def wrap_stream_with_cm_drop_matrix(xobj, cm_tuple):
    """在 AP stream 前插入 cm，拷貝字典但刪除 /Length /Filter /DecodeParms /Matrix。"""
    a,b,c,d,e,f = cm_tuple
    try:
        orig_bytes = xobj.get_data()
    except Exception:
        return None

    prefix = b"q\n%.6f %.6f %.6f %.6f %.6f %.6f cm\n" % (a,b,c,d,e,f)
    wrapped = prefix + orig_bytes + b"\nQ\n"

    meta = DictionaryObject()
    for k, v in xobj.items():
        if k in ("/Length", "/Filter", "/DecodeParms", "/Matrix"):
            continue
        meta[k] = v

    new = DecodedStreamObject()
    new.update(meta)
    new._data = wrapped
    return new

# ---- stamp AP fix: use inverse of original /Matrix ----
def fix_stamp_ap_by_inverting_matrix(annot):
    ap = annot.get("/AP")
    if not ap or "/N" not in ap:
        return False

    try:
        nref = ap["/N"]
        xobj = nref.get_object()
    except Exception:
        xobj = ap["/N"]

    # 讀原 /Matrix（若無則不處理）
    try:
        m = xobj.get("/Matrix")
        if not m or len(m) != 6:
            return False
        orig = tuple(float(v) for v in m)
    except Exception:
        return False

    inv = invert_affine(orig)

    # 🔑 在這裡加一個補 90° 的旋轉矩陣
    # 這裡用「順時針 90°」: [0 -1 1 0 0 w]
    bbox = list(xobj.get("/BBox", [0,0,0,0]))
    w = float(bbox[2] - bbox[0]) if len(bbox) == 4 else 0.0
    extra = (0, -1, 1, 0, 0, w)

    # 合併：先做 inv，再做 extra
    def mul(a,b):
        a1,b1,c1,d1,e1,f1 = a
        a2,b2,c2,d2,e2,f2 = b
        return (
            a1*a2 + c1*b2,
            b1*a2 + d1*b2,
            a1*c2 + c1*d2,
            b1*c2 + d1*d2,
            a1*e2 + c1*f2 + e1,
            b1*e2 + d1*f2 + f1
        )
    cm_final = mul(extra, inv)

    new_x = wrap_stream_with_cm_drop_matrix(xobj, cm_final)
    if new_x is None:
        return False

    ap[NameObject("/N")] = new_x
    # new_x 字典已經不包含 /Matrix；也清掉 /MK /R 避免再旋轉
    mk = annot.get("/MK")
    if mk and "/R" in mk:
        try:
            del mk[NameObject("/R")]
        except Exception:
            pass
    return True

def fix_fake_landscape(input_path, output_path):
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for pageno, page in enumerate(reader.pages, start=1):
        rot = page.rotation or 0
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)

        if rot == 270 and h > w:  # portrait 且 Rotate=270
            print(f"[Page {pageno}] portrait+Rotate=270 → normalize to true landscape")

            # 1) 擴正為正方形（避免裁切）
            L = max(w, h)
            page.mediabox = RectangleObject([0, 0, L, L])

            # 2) 把內容旋回正（+90 並平移 h）
            tf = Transformation().rotate(90).translate(h, 0)
            page.add_transformation(tf)

            # 3) 清掉 Rotate
            page.rotation = 0

            # 4) 裁回 landscape（寬>高）
            page.mediabox = RectangleObject([0, 0, h, w])

            # 5) 同步轉換所有註解的 Rect（用與頁面相同的前向矩陣）
            M = (0.0, 1.0, -1.0, 0.0, h, 0.0)
            annots = page.get("/Annots", []) or []
            for aref in annots:
                try:
                    annot = aref.get_object()
                except Exception:
                    annot = aref
                rect = annot.get("/Rect")
                if rect:
                    old = [float(rect[i]) for i in range(4)]
                    new = transform_rect(old, M)
                    annot[NameObject("/Rect")] = RectangleObject([NumberObject(v) for v in new])

            # 6) 對所有 Stamp：用「原 AP /Matrix 的逆」前置到 stream，並移除 /Matrix
            fixed = 0
            for aref in annots:
                annot = aref.get_object()
                subtype = annot.get("/Subtype")
                if subtype in (NameObject("/Stamp"), "/Stamp"):
                    if fix_stamp_ap_by_inverting_matrix(annot):
                        fixed += 1
            print(f"  → Stamp AP fixed by inverse-matrix: {fixed}")

        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)
    print("✅ 完成，輸出：", output_path)

# 直接執行
inputpdf  = r"C:\Users\user\Desktop\PDFTEST\Origin.pdf"
outputpdf = r"C:\Users\user\Desktop\PDFTEST\stamped.pdf"
fix_fake_landscape(inputpdf, outputpdf)



def batch_fix_fake_landscape(folder_path):
    # 建立輸出資料夾
    output_dir = os.path.join(folder_path, "fixed")
    os.makedirs(output_dir, exist_ok=True)

    # 掃描資料夾內所有 PDF
    for fname in os.listdir(folder_path):
        if fname.lower().endswith(".pdf"):
            inputpdf = os.path.join(folder_path, fname)
            name, ext = os.path.splitext(fname)
            outputpdf = os.path.join(output_dir, f"{name}_fixed{ext}")

            print(f"處理檔案: {fname} → {os.path.basename(outputpdf)}")
            try:
                fix_fake_landscape(inputpdf, outputpdf)
            except Exception as e:
                print(f"⚠️ {fname} 處理失敗: {e}")

    print("✅ 全部處理完成，輸出在:", output_dir)


# 範例呼叫
if __name__ == "__main__":
    folder = r"C:\Users\user\Desktop\PDFTEST\PDFpackage"
    batch_fix_fake_landscape(folder)
