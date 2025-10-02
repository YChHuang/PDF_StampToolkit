### 簡介
made by AI
AjustPDFsOreintation.py 針對PageOreintation錯誤的處理，包括stamp物件，目前只能修正(portrait, rotate = 270的假landscape)
PdfStampReplacer.py 可以把stamp蓋到另一份資料上，但要先保證oreintation正確。

### 背景
起初收到需求，需要將pdf上的印章蓋到另一份對應檔案上，由於數量有些龐大，我想到應該能用python+AI解決。
### 困難點
- 嘗試請AI寫了段貼印章的code，第一個遇到的問題是AI不知道什麼是印章，後來請AI寫一段print每頁的資訊，並比對沒有印章的頁面後  
得知印章annotation的標籤是"stamp" 。
- 請AI寫了段按照相對位置貼stamp的code後，發現有特定頁面會變形，無法正確貼上，之後請AI寫另一段code用來print每一頁的資訊，在比對正常與失敗的頁面後，  
發現有些頁面的orientation是landscape, rotate = 0;有些是protrait, rotate = 270，儘管他們看起來一樣。
- 因此先請AI寫一份修正裁切與旋轉的code，此時又出現新問題，stamp物件很頑固，其他物件都轉到正確位置，stamp仍舊會留在原本的位置， 後來才知道stamp有自己的ract+rotation和一個仿射矩陣，AI後來給的解方是用仿射矩陣的反矩陣硬編到ract上。
- 這樣統一能把轉向與裁切錯誤的頁面都正規化，之前的貼印章code就能用了。
- 理解這些後對後續下prompt給AI挺有幫助的，總之code就寫出來了。
