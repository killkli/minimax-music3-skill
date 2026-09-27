---
name: minimax-music3
description: 使用隨附的 Colab/Diffusers 流程或已啟動的 SGLang-Omni 端點，根據歌詞與音樂描述產生 MiniMax Music 3 歌曲。適用於使用者要求產生單首或批次音樂時。
---

# MiniMax Music 3

根據使用者提供的歌詞與音樂方向產生立體聲 WAV。依照使用者指定與目前環境選擇後端：

- 使用者要跑隨附的 Diffusers 流程，且已安裝並完成驗證 `colab` CLI 時，使用 Colab runner。請閱讀 [references/colab-runner.md](references/colab-runner.md)。
- 使用者提供或要求使用已啟動的本機 SGLang-Omni 服務時，使用該端點。請閱讀 [references/sglang.md](references/sglang.md)。
- 兩者都不可用時，說明需要準備的環境；不可假稱音樂已產生。

## 輸入

收集或保留以下內容：

- `lyrics`：要演唱的原始歌詞。段落標記如 `[Verse]`、`[Chorus]`、`[Bridge]` 或 `[Instrumental]` 請各自放在獨立一行。
- `music_description`：使用者指定的曲風、情緒、速度、人聲、樂器、編曲與製作方向。
- Colab/Diffusers 路徑的 `duration_seconds` 與 `seed`。若使用者沒指定，使用 notebook 預設的 10 秒與 seed 7。秒數是最長長度，範圍 1–300；模型可能提早結束。seed 必須介於 0 與 18,446,744,073,709,551,615 之間。

除非使用者要求，否則不要改寫歌詞或音樂限制。若沒有歌詞且使用者也沒說要純音樂，詢問使用者要提供歌詞還是改為純音樂。明確要求純音樂時，將 `[Instrumental]` 作為歌詞輸入。

若已安裝 `music-caption-rewriter`，且使用者要求協助撰寫 prompt，可用它擴寫音樂描述。該 skill 只處理文字，不會產生音訊。

## Colab/Diffusers 產生流程

使用 `scripts/runner.py` 搭配 UTF-8 JSON manifest。Runner 會從隨附 notebook 載入準備與產生儲存格、讓同一批工作共用一個 Colab session、每首完成後下載 WAV、驗證立體聲 PCM-16 音訊、原子寫入進度檔，並只停止自己建立的 session。

收到明確的音樂產生請求後，先查看 `colab version` 與 `colab usage`；Colab 推論會消耗使用者的運算單位。純 prompt 草擬、文件撰寫或其他未要求產生音訊的工作，不要配置 Colab 執行階段。Runner 會把 prompt 傳送至 Colab kernel；Colab CLI 也可能將執行程式碼保存在本機 `~/.config/colab-cli/history/`。若歌詞或描述屬機密，改用本機 SGLang 端點。不要把憑證放進 manifest 或產生的 Python 程式碼。公開的 Hugging Face 權重不需要 MiniMax API key。

隨附 notebook 需要支援 BF16 的 CUDA GPU。使用 A100 或 L4；T4 不支援此流程。顯存低於 24 GiB 時，系統 RAM 至少需要 32 GiB。預設模型快取位於 Colab 暫存磁碟；啟用 Google Drive 快取需互動式授權，適合手動使用 notebook。

Diffusers 路徑會先用 OpenCC `t2s` 將繁體中文歌詞與描述轉為簡體中文，再送入模型。輸出為 44.1 kHz 立體聲 PCM-16 WAV。SGLang 路徑則保留原始文字，通常輸出 32 kHz 立體聲 WAV。

## SGLang-Omni 產生流程

只呼叫使用者提供的端點，或已啟動且指定供本任務使用的本機服務。不要自行啟動 GPU 伺服器。請依照 [references/sglang.md](references/sglang.md) 設定請求欄位與處理輸出。

## 完成回報

產生後確認每個指定檔案存在，並通過後端音訊驗證。回報輸出路徑、長度、取樣率、聲道數，以及可取得的 seed。若批次後續工作失敗，保留並回報先前已完成的 WAV。逾時時先檢查進度檔與 Colab session 狀態；確認原工作已結束前，不要重複啟動推論。
