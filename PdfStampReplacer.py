from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    NameObject, ArrayObject, DictionaryObject, IndirectObject
)

# ---- helpers: clone resources and xobjects ----
def clone_resource_dict(writer: PdfWriter, res_dict: DictionaryObject) -> DictionaryObject:
    """
    深度克隆資源字典：針對常見類別（/XObject, /Font, /ExtGState, /Pattern, /ColorSpace）
    逐項建立新的間接物件並更新引用。
    """
    if not isinstance(res_dict, DictionaryObject):
        return res_dict

    new_res = DictionaryObject()
    for key, val in res_dict.items():
        # 只處理常見的資源類別；其他直接拷貝（通常不影響 stamp 顯示）
        if key in (NameObject("/XObject"), NameObject("/Font"),
                   NameObject("/ExtGState"), NameObject("/Pattern"),
                   NameObject("/ColorSpace")):
            if isinstance(val, DictionaryObject):
                sub = DictionaryObject()
                for nk, nv in val.items():
                    # nv 可能是 IndirectObject；取出實體後加入 writer
                    try:
                        obj = nv.get_object() if isinstance(nv, IndirectObject) else nv
                        new_ref = writer._add_object(obj)
                        sub[NameObject(nk)] = new_ref
                    except Exception:
                        sub[NameObject(nk)] = nv
                new_res[NameObject(key)] = writer._add_object(sub)
            else:
                # 不常見情況，盡量拷貝
                try:
                    new_res[NameObject(key)] = writer._add_object(val)
                except Exception:
                    new_res[NameObject(key)] = val
        else:
            # 其他資源原樣搬過去（必要時可擴充）
            new_res[NameObject(key)] = res_dict[key]
    return new_res

def clone_appearance_n(writer: PdfWriter, ap: DictionaryObject):
    """
    克隆 /AP 字典中的 /N（通常是 Form XObject）。
    - 搬運 XObject stream 自身
    - 搬運其 /Resources（並重寫內部引用）
    - 回傳新的 /AP 字典（只含 /N）
    """
    if not ap or "/N" not in ap:
        return None

    # 取出原 /N 外觀（可能是 IndirectObject）
    n_obj = ap["/N"]
    try:
        xobj = n_obj.get_object() if isinstance(n_obj, IndirectObject) else n_obj
    except Exception:
        xobj = n_obj

    # 把外觀 XObject 本身加入 writer
    new_xobj_ref = writer._add_object(xobj)
    new_xobj_dict = new_xobj_ref.get_object()

    # 如果有 /Resources，克隆並更新
    res = xobj.get("/Resources")
    if isinstance(res, DictionaryObject):
        new_res_dict = clone_resource_dict(writer, res)
        new_xobj_dict[NameObject("/Resources")] = writer._add_object(new_res_dict)

    # 構造全新的 /AP 字典（避免在 IndirectObject 上賦值）
    new_ap_dict = DictionaryObject()
    new_ap_dict[NameObject("/N")] = new_xobj_ref
    return writer._add_object(new_ap_dict)

def copy_single_stamp(writer: PdfWriter, annot_dict: DictionaryObject) -> IndirectObject:
    """
    深度複製單一 stamp 註解：
    - 複製註解字典本身
    - 深度複製 /AP /N 和其 /Resources
    - 移除 /P 引用（避免指向原檔 page）
    - 清掉 /MK /R（避免方向疊加）
    """
    # 建立新的註解字典副本，避免直接在 IndirectObject 上改
    new_annot_copy = DictionaryObject()
    for k, v in annot_dict.items():
        # 跳過 /AP，待會重建；/P 也移除避免指到原頁
        if k in (NameObject("/AP"), NameObject("/P")):
            continue
        new_annot_copy[NameObject(k)] = v

    # 清除 /MK /R（若存在）
    mk = annot_dict.get("/MK")
    if isinstance(mk, DictionaryObject) and "/R" in mk:
        mk_copy = DictionaryObject()
        for k2, v2 in mk.items():
            if k2 == NameObject("/R"):
                continue
            mk_copy[NameObject(k2)] = v2
        new_annot_copy[NameObject("/MK")] = mk_copy
    elif mk:
        new_annot_copy[NameObject("/MK")] = mk

    # 寫入新的註解物件
    new_annot_ref = writer._add_object(new_annot_copy)

    # 深度克隆 AP/N
    ap = annot_dict.get("/AP")
    if isinstance(ap, (DictionaryObject, IndirectObject)):
        ap_dict = ap.get_object() if isinstance(ap, IndirectObject) else ap
        new_ap_ref = clone_appearance_n(writer, ap_dict)
        if new_ap_ref:
            new_annot_ref.get_object()[NameObject("/AP")] = new_ap_ref
        else:
            # 沒有 AP/N 時，保留原狀或略過
            pass

    return new_annot_ref

# ---- main: copy stamps from stamped -> base ----
def copy_stamps(base_path, stamped_path, output_path):
    base_reader = PdfReader(base_path)
    stamped_reader = PdfReader(stamped_path)
    writer = PdfWriter()

    base_pages = len(base_reader.pages)
    stamped_pages = len(stamped_reader.pages)
    if stamped_pages > base_pages:
        print(f"⚠️ stamped PDF 頁數比 base 多，將只處理前 {base_pages} 頁")

    for i in range(base_pages):
        base_page = base_reader.pages[i]
        if i >= stamped_pages:
            break
        stamped_page = stamped_reader.pages[i]

        # 尺寸或方向不同，警告但繼續
        if (base_page.mediabox.width != stamped_page.mediabox.width or
            base_page.mediabox.height != stamped_page.mediabox.height or
            (base_page.rotation or 0) != (stamped_page.rotation or 0)):
            print(f"⚠️ Page {i+1}: base({base_page.mediabox}, rot={base_page.rotation or 0}) "
                  f"vs stamped({stamped_page.mediabox}, rot={stamped_page.rotation or 0}) 尺寸/旋轉不同")

        # 1) 移除 base 的 stamp
        base_annots = base_page.get("/Annots", [])
        kept = []
        removed = 0
        for aref in base_annots:
            obj = aref.get_object() if isinstance(aref, IndirectObject) else aref
            if obj.get("/Subtype") == "/Stamp":
                removed += 1
            else:
                kept.append(aref)
        if kept:
            base_page[NameObject("/Annots")] = ArrayObject(kept)
        elif "/Annots" in base_page:
            del base_page["/Annots"]

        # 2) 從 stamped 搬運 stamp（含外觀）
        added = 0
        stamped_annots = stamped_page.get("/Annots", [])
        if stamped_annots:
            if "/Annots" not in base_page:
                base_page[NameObject("/Annots")] = ArrayObject()
            for aref in stamped_annots:
                obj = aref.get_object() if isinstance(aref, IndirectObject) else aref
                if obj.get("/Subtype") == "/Stamp":
                    try:
                        new_stamp_ref = copy_single_stamp(writer, obj)
                        base_page["/Annots"].append(new_stamp_ref)
                        added += 1
                    except Exception as e:
                        print(f"    ⚠️ Page {i+1} 複製 stamp 失敗：{e}")

        print(f"Page {i+1}: 移除 {removed} 個 stamp，新增 {added} 個 stamp")
        writer.add_page(base_page)

    with open(output_path, "wb") as f:
        writer.write(f)

    print("✅ 完成，輸出：", output_path)




# 直接執行
base_pdf    = r"C:\Users\user\Desktop\PDFTEST\base.pdf"
stamped_pdf = r"C:\Users\user\Desktop\PDFTEST\stamped.pdf"
output_pdf  = r"C:\Users\user\Desktop\PDFTEST\merged.pdf"

copy_stamps(base_pdf, stamped_pdf, output_pdf)