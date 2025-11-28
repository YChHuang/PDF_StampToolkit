from collections import defaultdict
from pypdf import PdfReader

def analyze_pdf_orientation(input_pdf, output_pdf=None):
    reader = PdfReader(input_pdf)

    # 用 dict 分類頁面
    categories = defaultdict(list)

    for pageno, page in enumerate(reader.pages, start=1):
        rot = page.rotation or 0
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)

        orientation = "Landscape" if w > h else "Portrait"
        key = f"{orientation}_{rot}"

        # 分類
        categories[key].append(pageno)

        # 打印每頁資訊
        print(f"[Page {pageno}] orientation={orientation}, rotation={rot}, size={int(w)}x{int(h)}")

    print("\n=== 結論 ===")
    if len(categories) == 1:
        only_key = list(categories.keys())[0]
        print(f"全部統一 → {only_key}, pages={categories[only_key]}")
    else:
        print("不統一，分類如下：")
        for key, pages in categories.items():
            print(f"  {key} = {pages}")

    if output_pdf:
        print(f"\n(此分析不會修改 PDF，只是檢查) → 輸出檔案路徑: {output_pdf}")


# 入口
input_pdf    = r"C:\Users\user\Desktop\PDFTEST\Origin.pdf"
output_pdf   = r"C:\Users\user\Desktop\PDFTEST\WrongOrientSinglePage_chatGPT.pdf"

analyze_pdf_orientation(input_pdf, output_pdf)
