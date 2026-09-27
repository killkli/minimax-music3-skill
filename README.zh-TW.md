# MiniMax Music 3 Agent Skill

這是一個獨立的 Agent skill，可根據歌詞與音樂描述產生 MiniMax Music 3 歌曲。它將 Colab/Diffusers notebook 包裝成可重複使用的批次流程，並提供已啟動 SGLang-Omni 服務的 API 使用方式。

## 內容

- `SKILL.md`：Agent 指令與後端選擇方式。
- `scripts/runner.py`：使用 Python 標準函式庫撰寫的 Google Colab CLI 批次 runner。
- `assets/MiniMax_Music3_Colab.ipynb`：依據目前 MiniMax Music 3 repo 流程整理的 Colab notebook。
- `references/`：Colab runner 與 SGLang 端點說明，只有需要時才載入。
- `install.sh`：冪等且不覆蓋既有資料的 Codex skill 安裝器。
- `README.en.md` 與 `SKILL.zh-TW.md`：英文文件與繁體中文 skill 翻譯。

本 repo 不包含模型權重或產生的音訊。

## 安裝 skill

安裝時需要 Bash 與 Codex skills 目錄。預設目錄為 `$CODEX_HOME/skills`；若沒有設定 `CODEX_HOME`，則使用 `~/.codex/skills`。

```bash
git clone https://github.com/killkli/minimax-music3-skill.git
cd minimax-music3-skill
./install.sh
```

若 `$CODEX_HOME/skills/minimax-music3` 已存在，安裝器預設保留原目錄。使用 `--force` 才會替換，且舊目錄會先移至附有時間戳記的備份路徑。要安裝到其他支援 skill 的 Agent 目錄，請指定絕對路徑：

```bash
./install.sh --dest /absolute/path/to/skills
```

skill 名稱是 `minimax-music3`。若 Agent 會快取 skill 清單，安裝後請開啟新 turn 或重新整理清單。

## 透過 Colab 產生音樂

Runner 本身需要 Python 3.11 以上版本。目前的 [`google-colab-cli`](https://pypi.org/project/google-colab-cli/) 0.7.4 則需要在自己的安裝環境使用 Python 3.12 以上版本，因此 runner 與 CLI 可使用不同的 Python。Colab 也必須已完成驗證，且帳戶能配置支援 BF16 的 A100 或 L4 GPU；可用機型、方案配額及運算單位餘額都會影響能否執行。Runner 會在配置 GPU 前檢查 `colab version` 與 `colab usage`。

先建立 UTF-8 JSON manifest：

```json
{
  "jobs": [
    {
      "id": "demo",
      "lyrics": "[Verse]\n紙船漂過黃昏的溪流\n[Chorus]\n安靜星光開始閃爍",
      "music_description": "溫柔原音流行曲，親密的女聲主唱、指彈吉他、柔和鋼琴，並逐漸推進到最後一段副歌。",
      "duration_seconds": 30,
      "seed": 7
    }
  ]
}
```

執行整批工作：

```bash
python3 scripts/runner.py \
  --manifest /absolute/path/jobs.json \
  --gpu A100 \
  --high-mem \
  --timeout 10800 \
  --output-dir /absolute/path/music3-output
```

Runner 支援 `--gpu A100|L4`、`--high-mem`、`--timeout`、`--provision-timeout` 與 `--progress`。未指定時，秒數預設 10 秒、seed 預設 7。秒數必須為 1–300 的整數，代表最長時間，模型可能提早停止。Colab/Diffusers seed 範圍為 0–18,446,744,073,709,551,615。段落標籤請各自放在獨立一行。完整範例請見 [`examples/jobs.json`](examples/jobs.json)。

Runner 每批只啟動一個 Colab session，載入一次模型，並在每首完成後立即下載。輸出為 `id_seedN.wav`，進度檔為 `progress.json`。進度檔包含工作 ID、seed、狀態、輸出路徑與 WAV 資訊，不會保存歌詞或音樂描述。Colab CLI 0.7.4 也會將執行程式碼記錄在本機 `~/.config/colab-cli/history/`，Runner 會將 prompt 傳送到遠端 Colab kernel。機密歌詞或描述請改用本機 SGLang 端點。若同名輸出已存在，Runner 會拒絕覆寫。Runner 會嘗試停止自行配置的 session，即使配置逾時或中斷也會清理。

Notebook 會安裝 Diffusers 0.40.0、Transformers、Accelerate、SoundFile 與 OpenCC，並從 Hugging Face 載入 `MiniMaxAI/MiniMax-Music3`，不需要 MiniMax API key。Notebook 需要支援 BF16 的 GPU；顯存低於 24 GiB 時，系統 RAM 至少要有 32 GiB。輸出為 44.1 kHz 立體聲 PCM-16 WAV。輸入中的繁體中文歌詞與描述會先轉為簡體中文。

例如，可用 `uv` 為 Colab CLI 安裝支援的 Python 版本：

```bash
uv python install 3.12
uv tool install --python 3.12 google-colab-cli
```

若要互動操作或將模型快取在 Google Drive，請在 Colab 開啟 `assets/MiniMax_Music3_Colab.ipynb`，並依照 notebook 的說明操作。掛載 Drive 需要互動式授權。完整 manifest 與清理流程請見 [`references/colab-runner.md`](references/colab-runner.md)。

## 使用 SGLang-Omni 端點

如果使用者已有設定好的 SGLang-Omni Music 3 服務，將歌詞放在 `/v1/audio/speech` 請求的 `input` 欄位，音樂描述放在 `instructions`。本 repo 的範例使用模型名稱 `minimax_ttm`、seed、WAV 格式與非串流輸出。SGLang 路徑會保留原始輸入文字，通常回傳 32 kHz 立體聲音訊。範例 API 沒有保證精確秒數的 `duration_seconds` 欄位。細節請見 [`references/sglang.md`](references/sglang.md)。

此 skill 不會安裝或啟動 SGLang-Omni，也不會配置本機 GPU。範例 URL 使用 localhost，不代表服務一定已啟動。

## 輸入與資料處理

- 除非使用者要求修改，否則保留歌詞與明確的音樂限制。
- Colab runner 會把 prompt 文字放在送往遠端 Colab kernel 的程式碼中。請勿在歌詞、描述或 manifest 中放入憑證或秘密。
- Colab session 會消耗帳戶運算單位。只有實際要求產生音訊時才使用 Colab；Runner 會在結束時停止自己建立的 session。
- Runner 的進度檔會保存工作 ID、seed、輸出路徑與 WAV 資訊，不含 prompt 文字。
- 遇到逾時時，先檢查 `progress.json` 與指定 session，再決定是否重試，以免重複工作並消耗運算單位。

## 授權與出處

本 repo 原創的 skill 指令、runner、安裝器與文件採 MIT 授權。隨附 notebook 在 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) 中另行標示，並隨附 MiniMax Music 3 Community License。該上游授權包含可接受使用政策與商業條款；本 repo 的 MIT 授權不會取代它。模型權重於執行時才從 Hugging Face 下載，本 repo 不包含權重。

MiniMax Music 3、Google Colab、Hugging Face、Diffusers、Transformers、OpenCC 與 SGLang-Omni 都是第三方專案或服務。使用或散布模型、輸出或託管服務前，請閱讀各自最新的授權與服務條款。

## 離線檢查

以下指令不會配置 Colab session，也不會消耗運算單位：

```bash
python3 scripts/runner.py --help
python3 -m py_compile scripts/runner.py
bash -n install.sh
```

## 參考

Repository 結構與安裝器參考了 [minimax-h3-colab-skill](https://github.com/killkli/minimax-h3-colab-skill)。音樂流程與隨附 notebook 取自目前本機 MiniMax Music 3 repo，並參考了 [官方模型文件](https://huggingface.co/MiniMaxAI/MiniMax-Music3)。
