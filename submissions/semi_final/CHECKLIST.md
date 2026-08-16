# 澶嶈禌鎻愪氦娓呭崟 路 绠楁硶璧?路 鏂瑰悜涓?路 闃熶紞銆屽拰鏄嗕粦銆?

> 渚濇嵁锛歚document/AI_for_reserach0816.md`锛涙埅姝?~2026-09-03锛堜互瀹樼綉涓哄噯锛? 
> 鍛藉悕锛歚AI4R_ALG_MAT_鍜屾槅浠?zip`  
> **鍗＄偣涓庝汉宸ユ楠わ細** [`SUPPORT_NEEDED.md`](SUPPORT_NEEDED.md)

## 鎵嬪唽蹇呬氦

- [x] 鍙繍琛屼唬鐮佷粨搴?+ `REPRODUCE.md`
- [x] 瀹為獙缁撴灉 + 绉戝鎰忎箟 + 渚濊禆鎶湶
- [x] 鍩烘湰浠诲姟 PDF+LaTeX + 绯荤粺璇存槑
- [x] Sci-Base 鎺ュ叆锛堢紦瀛?+ enrich 璺戞 `production_sciverse_scibase`锛?
- [x] 璺嚎 A 瑙ｉ噴鏂囨。 + 鏋勬晥/澶栭獙浜х墿
- [x] 寮曠敤鑷煡 `citation_audit.md`锛圤penAlex DOI锛?
- [x] 鎶€鏈姤鍛婅崏绋?+ 涓€椤电焊棰勭 + LICENSE(Apache-2.0)
- [x] Dockerfile + MCP 璇存槑鏂囨。
- [ ] **瀹屾暣 hybrid 閲戞爣閲嶈窇**锛堥渶 Docker锛夆€?瑙?SUPPORT 搂1
- [ ] **L2 鐪熶汉绛惧瓧 鈮?** 鈥?瑙?SUPPORT 搂2
- [ ] **鍏紑浠撳簱 URL** 鈥?瑙?SUPPORT 搂3

## 鍐插垎

- [x] GA 鍙欎簨 + LLM 娑堣瀺
- [x] MP + OQMD 鍙屽簱澶栭獙
- [x] MinerU/GROBID 鎶湶鍙ｅ緞
- [ ] coverage鈮?.5锛堝彲閫夋墿鏍囷紱褰撳墠鈮?.30 涓嶄綔涓诲浼狅級
- [ ] Sciverse 瀹樻柟 MCP锛堝彲閫夛紱REST 宸插悎瑙勶級

## 閲嶆柊鎵撳寘

```powershell
cd submissions\scripts
powershell -ExecutionPolicy Bypass -File .\build_submission_packages.ps1 -SemiFinal
```

