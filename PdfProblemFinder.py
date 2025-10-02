from pypdf import PdfReader

def print_pdf_page_info(pdf_path: str):
    reader = PdfReader(pdf_path)
    num_pages = len(reader.pages)
    print(f"PDF has {num_pages} pages\n")

    for i, page in enumerate(reader.pages, start=1):
        # 頁面尺寸 (單位: pt, 1 pt = 1/72 inch)
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        # 判斷方向
        orientation = "Landscape" if width > height else "Portrait"

        # 頁面旋轉角度 (可能是 0, 90, 180, 270)
        rotation = page.get("/Rotate", 0)
        print(pdf_path)
        print(f"Page {i}:")
        print(f"  Size       : {width:.2f} x {height:.2f} pt")
        print(f"  Orientation: {orientation}")
        print(f"  Rotation   : {rotation}°")
        print()


from pypdf import PdfReader

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


input_pdf    = r"C:\Users\user\Desktop\PDFTEST\WrongOrientSinglePage.pdf"
output_pdf  = r"C:\Users\user\Desktop\PDFTEST\WrongOrientSinglePage_chatGPT.pdf"

#findout each page diff

# print_pdf_page_info(input_pdf)
# print_pdf_page_info(output_pdf)


# find out each stamp diff
print_page1_stamps(input_pdf)
print_page1_stamps(output_pdf)