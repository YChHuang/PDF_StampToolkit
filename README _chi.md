# PDF修正假橫向PDF與自動蓋章小工具

## 功能介紹與使用方法

### 功能介紹 

用 [ExminePdfOrientation.py](Scripts/ExminePdfOrientation.py) 檢查是否需要修正pdf，  
會像這樣(OrientationType_Rotation = [])：  

```
不統一，分類如下：
  Landscape_0 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 134, 135, 136]
  Portrait_270 = [34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133]
```

這樣就抓出有內鬼了

然後[AjustPDFsOrientation.py](Scripts/AjustPDFsOrientation.py)能將portrait, rotate = 270的假landscape變成真的landscape   

而 [PdfStampReplacer.py](Scripts/PdfStampReplacer.py) 可以把stamp蓋到另一份資料上，但要先保證oreintation正確，所以遇到雜亂的檔案可以用前面的工具先歸零。

### 基本用法
檔案內每一個.py底下都有兩個變數input_pdf 和 output_pdf   
幫這兩個變數依序指定為輸入的pdf及輸出路徑(輸出檔案可以不存在，但要用.pdf結尾，此外請特別注意，檔案若存在會直接取代掉，沒有警告)
執行腳本即可，我是用vs code直接跑

## 技術棧
Python 3.13  
pypdf 6.1.0

## 背景

收到需求，需要將pdf上的印章蓋到另一份對應檔案上，由於數量有好幾千頁，不想手動貼，想到能用python+AI解決。  
後來查資料後，得知有pypdf這類庫可以編輯pdf，因此此想法可行。

直接請AI生成蓋章腳本，首先遇到一個問題，有部分頁面印章會亂蓋，找不到原因。  
請AI多log幾個資訊後，發現是有騙子landscape，它的原貌是portrait+270度的rotation  
因此將問題拆成：轉正與蓋印章。 

轉正問題：測試幾個prompt後，AjustPDFsOrientation.py誕生。

蓋印章問題：  
第一個遇到的問題是AI不知道什麼是印章。  
請AI寫一段print每頁的資訊，並比對沒有印章的頁面後，得知印章annotation的標籤是"stamp"。  
後續用annotation和stamp等詞彙，便能精準指出我的需求。

拿資料測試了一下，目前版本可以完成任務，版本先停在這裡。

## 筆記

### 修正旋轉方向:

PDF 的畫面幾何實際分成三層：

- Page 世界（全域座標）
- Annotation Rect 世界（互動框世界）
- Stamp local 世界（stamp的local繪圖世界）

它們彼此獨立、具語意層級關係，但不會自動同步。

### Page

Page 內主要由 MediaBox 與 /Rotate 定義世界座標。

在「假橫向 PDF」中，內容其實已經被物理旋轉，但仍殘留 `/Rotate=270` 的邏輯標記。

此流程會直接把 Page 世界轉正：

```python
tf = Transformation().rotate(90).translate(h, 0)
page.add_transformation(tf)
page.mediabox = RectangleObject([0, 0, h, w])
page.rotation = 0
```
也就是把整個世界逆時針旋轉 90° 並平移回第一象限，並同步交換紙張邊界  


### Annots

Annotation Rect 是定義在 Page 世界中的資料欄位，不會自動跟隨 Page CTM。  

因此必須對所有 /Rect 套用同一組同步仿射矩陣，  
讓互動框仍維持在正確的頁面座標位置。  

### Stamps

Stamp 的實際顯示是：
```
Final = PageCTM · ( StampLocalCTM · Geometry )
```
當 PageCTM 被改寫後，Stamp會變成：
```
Final = (PageCTM · M) · ( StampLocalCTM · Geometry )
```
Stamp被多套了一次 M。  

為了讓畫面維持原本正確顯示，需要把 Stamp local 世界轉譯到新世界：  
```
StampLocalCTM := M⁻¹ · StampLocalCTM
```
也就是在 Stamp AP stream 內插入反矩陣並移除舊 /Matrix。  

這樣才能在新 Page 世界下維持相同的最終畫面位置與幾何語意。  
