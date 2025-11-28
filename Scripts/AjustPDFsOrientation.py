from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject, NameObject, NumberObject

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
    normal = ap.get("/N")
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

        if rot == 270 and h > w:
            print(f"[Page {pageno}] normalize orientation + fix annots/stamps")

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
            print(f"  → Stamp AP fixed: {fixed}")

        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)
    print("✅ 完成，輸出：", output_path)

input_pdf    = r"C:\Users\user\Desktop\PDFTEST\WrongOrientSinglePage.pdf"
output_pdf  = r"C:\Users\user\Desktop\PDFTEST\WrongOrientSinglePage_chatGPT.pdf"

fix_fake_landscape_safe(input_pdf, output_pdf)
