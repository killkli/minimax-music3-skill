---
name: minimax-music3
description: Generate MiniMax Music 3 songs from lyrics and a music description using the bundled Colab/Diffusers workflow or an already-running SGLang-Omni endpoint. Use when a user asks to create or batch-generate Music 3 audio.
---

# MiniMax Music 3

Generate a stereo WAV from the user's lyrics and musical direction. Choose a backend based on the user's environment and request:

- Use the Colab runner when the user wants the bundled Diffusers workflow and the `colab` CLI is installed and authenticated. Read [references/colab-runner.md](references/colab-runner.md).
- Use SGLang-Omni when the user provides or requests an already-running local service endpoint. Read [references/sglang.md](references/sglang.md).
- If neither backend is available, explain the concrete setup needed; do not pretend a track was generated.

## Inputs

Collect or preserve:

- `lyrics`: exact words to sing, with structural tags such as `[Verse]`, `[Chorus]`, `[Bridge]`, or `[Instrumental]` on their own lines.
- `music_description`: genre, mood, tempo when specified, vocal direction, instrumentation, arrangement, and production.
- `duration_seconds` and `seed` for the Colab/Diffusers path. If omitted, use the notebook defaults of 10 seconds and seed 7. Duration is a maximum from 1 to 300 seconds; the model may stop earlier. Seed must be an integer from 0 to 18,446,744,073,709,551,615.

Do not rewrite lyrics or musical constraints unless asked. If lyrics are missing and the user has not asked for an instrumental, ask for lyrics or whether to make the track instrumental. For an explicitly instrumental request, use `[Instrumental]` as the lyrics input.

The optional `music-caption-rewriter` skill can expand the music description when it is installed and the user requests prompt help. It does not generate audio.

## Colab/Diffusers generation

Use the bundled `scripts/runner.py` with a UTF-8 JSON manifest. Resolve the script relative to this skill's installed directory; do not assume it is under the user's current project directory. The runner loads the bundled notebook's setup and generation cells, reuses one Colab session for the batch, downloads each WAV as it finishes, validates stereo PCM-16 audio, writes atomic progress state, and stops only the session it created.

Before a real generation request, check `colab version` and `colab usage`; Colab inference uses the user's compute units. Do not allocate a runtime for prompt drafting, documentation, or other tasks that did not request audio generation. Do not put credentials in a manifest or generated Python code. The runner sends prompt text to the Colab kernel, and Colab CLI may also keep executed code in local history under `~/.config/colab-cli/history/`. For confidential lyrics or descriptions, use a local SGLang endpoint instead. The public Hugging Face checkpoint does not require a MiniMax API key.

The bundled notebook requires a CUDA GPU with BF16 support. Use an A100 or L4 runtime; a T4 does not support this workflow. Below 24 GiB VRAM, the notebook needs at least 32 GiB system RAM. Its default cache is temporary Colab storage; enabling Google Drive cache requires an interactive Drive authorization and is intended for manual notebook use.

The Diffusers path converts Traditional Chinese lyrics and description to Simplified Chinese with OpenCC `t2s` before inference. It writes 44.1 kHz stereo PCM-16 WAV. The SGLang path keeps the supplied text unchanged and normally returns 32 kHz stereo WAV.

## SGLang-Omni generation

Only call an endpoint the user supplied or a local service that is already running and intended for this task. Do not start a GPU server implicitly. Follow [references/sglang.md](references/sglang.md) for the request fields and output handling.

## Completion report

After generation, confirm every requested file exists and passes the backend's audio validation. Report output paths, duration, sample rate, channels, and seed where available. If a later job fails, preserve and report earlier completed WAVs. On a timeout, inspect the progress file and Colab session state before retrying; do not start a duplicate generation while the first may still be running.
