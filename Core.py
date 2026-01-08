
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject, NameObject, NumberObject
from collections import Counter

def print_pdf_page_info(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    total = len(reader.pages)

    stats = Counter()
    for page in reader.pages:
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        orient = "Landscape" if w > h else "Portrait"
        rot = page.get("/Rotate", 0)
        stats[(orient, rot)] += 1

    combos = [
        ("Portrait", 0), ("Portrait", 90), ("Portrait", 180), ("Portrait", 270),
        ("Landscape", 0), ("Landscape", 90), ("Landscape", 180), ("Landscape", 270),
    ]

    lines = []
    lines.append(f"PDF has {total} pages\n")
    lines.append("Orientation / Rotation statistics:")

    for orient, rot in combos:
        count = stats.get((orient, rot), 0)
        lines.append(f"  {orient:10s} / {rot:3d}° : {count} pages")

    # 是否全部一致
    non_zero = [(k, v) for k, v in stats.items() if v > 0]
    if len(non_zero) == 1:
        (orient, rot), cnt = non_zero[0]
        lines.append("")
        lines.append("All pages share the same geometry:")
        lines.append(f"  {orient} / {rot}° ({cnt} pages)")
        lines.append("This PDF does NOT require geometry normalization.")

    return "\n".join(lines)


def print_page1_stamps(pdf_path: str):
    reader = PdfReader(pdf_path)
    page = reader.pages[0]  # 只讀第 1 頁
    
    annots = page.get("/Annots")
    if not annots:
        print("Page 1 has no annotations.")
        return
    
    print(f"Stamps on Page 1 of {pdf_path}:\n")
    for i, annot_ref in enumerate(annots, start=1):
        annot = annot_ref.get_object()
        subtype = annot.get("/Subtype")
        if subtype == "/Stamp":
            rect = annot.get("/Rect")
            name = annot.get("/Name")
            contents = annot.get("/Contents")
            ap = annot.get("/AP")
            matrix = None
            if ap and ap.get("/N") and ap.get("/N").get("/Matrix"):
                matrix = ap.get("/N").get("/Matrix")
            
            print(f"Stamp {i}:")
            print(f"  Rect     : {rect}")
            print(f"  Name     : {name}")
            print(f"  Contents : {contents}")
            print(f"  Matrix   : {matrix}")
            print()



def transform_rect(rect, M):
    """套用仿射矩陣到矩形"""
    x0, y0, x1, y1 = rect
    pts = [(x0, y0), (x1, y1)]
    new_pts = []
    for (x, y) in pts:
        new_x = M[0]*x + M[2]*y + M[4]
        new_y = M[1]*x + M[3]*y + M[5]
        new_pts.append((new_x, new_y))
    (nx0, ny0), (nx1, ny1) = new_pts
    return [min(nx0, nx1), min(ny0, ny1), max(nx0, nx1), max(ny0, ny1)]

def fix_stamp_ap_by_inverting_matrix(annot):
    ap = annot.get("/AP")
    if not ap:
        return False
    normal = ap.get("/N").get_object()

    if not normal:
        return False
    matrix = normal.get("/Matrix")
    if not matrix:
        return False

    try:
        a, b, c, d, e, f = [float(v) for v in matrix]
        det = a*d - b*c
        if abs(det) < 1e-6:
            return False
        inv = [ d/det, -b/det, -c/det, a/det,
                (c*f - d*e)/det, (b*e - a*f)/det ]

        stream = normal.get_object()
        old_data = stream.get_data()
        new_prefix = f"q {inv[0]} {inv[1]} {inv[2]} {inv[3]} {inv[4]} {inv[5]} cm\n".encode()
        new_data = new_prefix + old_data + b"\nQ\n"

        stream.set_data(new_data)  # ✅ 正確更新
        if "/Matrix" in normal:
            del normal["/Matrix"]
        return True
    except Exception as e:
        print("fix_stamp_ap error:", e)
        return False

def fix_fake_landscape_safe(input_path, output_path):
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for pageno, page in enumerate(reader.pages, start=1):
        rot = page.rotation or 0
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)

        # 判斷 orientation
        orientation = "Landscape" if w > h else "Portrait"
        print(f"[Page {pageno}] orientation={orientation}, rotation={rot}, size={int(w)}x{int(h)}")

        if rot == 270 and h > w:
            print(f"  → normalize orientation + fix annots/stamps")

            # 旋轉內容
            tf = Transformation().rotate(90).translate(h, 0)
            page.add_transformation(tf)
            page.mediabox = RectangleObject([0, 0, h, w])
            page.rotation = 0

            # 修正所有註解矩形
            M = (0, 1, -1, 0, h, 0)  # 同步矩陣
            annots = page.get("/Annots", []) or []
            for aref in annots:
                annot = aref.get_object()
                rect = annot.get("/Rect")
                if rect:
                    old = [float(rect[i]) for i in range(4)]
                    new = transform_rect(old, M)
                    annot[NameObject("/Rect")] = RectangleObject([NumberObject(v) for v in new])

            # 修正所有 Stamp
            fixed = 0
            for aref in annots:
                annot = aref.get_object()
                if annot.get("/Subtype") == NameObject("/Stamp"):
                    if fix_stamp_ap_by_inverting_matrix(annot):
                        fixed += 1
            print(f"    → Stamp AP fixed: {fixed}")

            # 修正後再印一次
            w2 = float(page.mediabox.width)
            h2 = float(page.mediabox.height)
            orientation2 = "Landscape" if w2 > h2 else "Portrait"
            print(f"    → after fix: orientation={orientation2}, rotation={page.rotation}, size={int(w2)}x{int(h2)}")

        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)
    print("✅ 完成，輸出：", output_path)




# input_pdf    = r"C:\Users\user\Desktop\PDFTEST\WrongOrientSinglePage.pdf"
# output_pdf   = r"C:\Users\user\Desktop\PDFTEST\WrongOrientSinglePage_chatGPT.pdf"

# print_pdf_page_info(input_pdf)
# #print_page1_stamps(input_pdf)
# fix_fake_landscape_safe(input_pdf, output_pdf)
# print_pdf_page_info(output_pdf)


#API
def analyze(pdf_path: str) -> str:
    
    return print_pdf_page_info(pdf_path)

def fix(input_pdf: str, output_pdf: str):
    fix_fake_landscape_safe(input_pdf, output_pdf)