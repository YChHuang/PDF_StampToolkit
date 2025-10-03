## 開發日誌
- AdjustPDFsOrientation.py 針對PageOrientation錯誤的處理，包括stamp物件，目前只能修正(portrait, rotate = 270的假landscape)
- PdfStampReplacer.py 可以把stamp蓋到另一份資料上，但要先保證oreintation正確。

### 背景
收到需求，需要將pdf上的印章蓋到另一份對應檔案上，由於數量有些龐大，想到能用python+AI解決。  
後來查資料後，得知有pypdf這類庫可以編輯pdf，因此此想法可行。

### 困難點
##### 將需求組織成與AI能聽懂的prompt：
- 嘗試請AI寫了段貼印章的code，第一個遇到的問題是AI不知道什麼是印章，後來請AI寫一段print每頁的資訊，並比對沒有印章的頁面後  
得知印章annotation的標籤是"stamp"。
- 後續用annots和stamp等詞彙，便能精準指出我的需求。
##### AI無法理解錯誤：
- 請AI寫了段按照相對位置貼stamp的code後，發現有特定頁面會變形怪異，無法正確貼上。
- 後續請AI寫一份能夠print出每個頁面的資訊的腳本，於是我比對正確與錯誤的葉面後，  
發現有些頁面的orientation是landscape, rotate = 0;有些是portrait, rotate = 270，儘管他們看起來一樣。
- 因此我想到應該先統一所有pdf的尺寸及轉向，因此縮小問題變成首先要解決正規化問題。
- 正規化也遇到不少瓶頸，stamp物件很頑固，其他物件都轉到正確位置，stamp仍舊會留在原本的位置， 後來才知道stamp有自己的rect+rotation和一個仿射矩陣，AI後來給的解方是用仿射矩陣的反矩陣硬編到rect的座標上。
### 收穫
- 理解了pdf渲染的原理以及常見pdf問題
- 在pdf領域與AI溝通更有效率
