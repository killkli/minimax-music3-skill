# MiniMax Music 3 Agent Skill

A standalone agent skill for creating MiniMax Music 3 songs from lyrics and a music description. It packages the Colab/Diffusers notebook as a repeatable batch workflow and documents the SGLang-Omni speech endpoint for users who already run that service.

## What is included

- `SKILL.md` — agent instructions and backend selection.
- `scripts/runner.py` — Python standard-library batch runner for Google Colab CLI.
- `assets/MiniMax_Music3_Colab.ipynb` — the Colab notebook adapted from the current MiniMax Music 3 repository workflow.
- `references/` — Colab runner and SGLang endpoint details loaded only when needed.
- `install.sh` — idempotent, non-destructive Codex skill installer.
- `README.zh-TW.md` and `SKILL.zh-TW.md` — Traditional Chinese documentation and skill translation.

Model weights and generated audio are not included.

## Install the skill

Requirements for installing are Bash and a Codex skills directory. The default is `$CODEX_HOME/skills` when `CODEX_HOME` is set, otherwise `~/.codex/skills`.

```bash
git clone https://github.com/killkli/minimax-music3-skill.git
cd minimax-music3-skill
./install.sh
```

By default, an existing `$CODEX_HOME/skills/minimax-music3` installation is preserved. To replace it, pass `--force`; the old directory is first moved to a timestamped backup. To install into another compatible agent's skill directory, provide its absolute path:

```bash
./install.sh --dest /absolute/path/to/skills
```

The skill name is `minimax-music3`. Start a new agent turn or refresh the skill list if the client caches installed skills.

## Generate through Colab

The runner requires Python 3.11+. Current [`google-colab-cli`](https://pypi.org/project/google-colab-cli/) 0.7.4 requires Python 3.12+ in its own install environment, so the runner and CLI may use separate interpreters. Colab must be authenticated and able to allocate an A100 or L4 GPU with BF16 support; account plan, quota, and compute-unit availability apply. The runner checks `colab version` and `colab usage` before provisioning.

Create a UTF-8 JSON manifest:

```json
{
  "jobs": [
    {
      "id": "demo",
      "lyrics": "[Verse]\nPaper boats cross the evening stream\n[Chorus]\nThe quiet stars begin to gleam",
      "music_description": "Gentle acoustic pop, intimate female lead, fingerpicked guitar, soft piano, and a gradual final chorus build.",
      "duration_seconds": 30,
      "seed": 7
    }
  ]
}
```

Then run the batch:

```bash
python3 scripts/runner.py \
  --manifest /absolute/path/jobs.json \
  --gpu A100 \
  --high-mem \
  --timeout 10800 \
  --output-dir /absolute/path/music3-output
```

Supported runner options are `--gpu A100|L4`, `--high-mem`, `--timeout`, `--provision-timeout`, and `--progress`. If omitted, duration defaults to 10 seconds and seed to 7. Duration must be an integer from 1 to 300 seconds; it is a maximum and generation may stop earlier. Colab/Diffusers seed values range from 0 to 18,446,744,073,709,551,615. Section tags should be on their own lines. See [`examples/jobs.json`](examples/jobs.json) for a complete manifest.

The runner starts one Colab session per batch, loads the model once, and downloads each song as soon as it completes. It writes `id_seedN.wav` and `progress.json` under the output directory. Progress contains job status and output metadata but not lyric or music-description text. Colab CLI 0.7.4 also records executed code in local history under `~/.config/colab-cli/history/`, and the runner sends prompts to the remote Colab kernel. Do not use this route for confidential lyrics or descriptions; use a local SGLang endpoint instead. Existing output paths are never overwritten. The runner attempts to stop the uniquely named session it requested, including if provisioning times out or is interrupted.

The notebook installs Diffusers 0.40.0, Transformers, Accelerate, SoundFile, and OpenCC. It loads `MiniMaxAI/MiniMax-Music3` from Hugging Face without a MiniMax API key. The notebook requires BF16 support; below 24 GiB of VRAM it needs at least 32 GiB system RAM. The output is 44.1 kHz stereo PCM-16 WAV. Traditional Chinese in both input fields is converted to Simplified Chinese before inference.

For example, install the Colab CLI with its supported Python interpreter using `uv`:

```bash
uv python install 3.12
uv tool install --python 3.12 google-colab-cli
```

For interactive use or Google Drive model caching, open `assets/MiniMax_Music3_Colab.ipynb` in Colab and follow the notebook's instructions. Drive mounting needs interactive authorization. See [`references/colab-runner.md`](references/colab-runner.md) for the full manifest and cleanup contract.

## Use an SGLang-Omni endpoint

If the user already has a configured SGLang-Omni Music 3 server, send the lyrics in `input` and the music description in `instructions` to `/v1/audio/speech`. The repository example uses model name `minimax_ttm`, seed, WAV format, and non-streaming output. The SGLang path preserves supplied text and normally returns 32 kHz stereo audio. It does not accept an exact `duration_seconds` guarantee through the example API. See [`references/sglang.md`](references/sglang.md).

The skill does not install or start SGLang-Omni or provision local GPUs. Do not assume an endpoint is running because the sample URL uses localhost.

## Input and data handling

- Keep lyrics and explicit musical constraints unchanged unless the user asks for editing.
- The Colab runner sends the prompt text to the remote Colab runtime as part of its generation code. Do not include credentials or secrets in lyrics, descriptions, or manifests.
- Colab sessions consume account compute units. Use the Colab route only for an actual generation request; the runner stops the session it owns after the batch.
- The runner's progress file stores job IDs, seeds, output paths, and WAV metadata. It does not store prompt text.
- On timeout, inspect `progress.json` and the named session before retrying to avoid duplicate work and compute use.

## License and attribution

The original skill instructions, runner, installer, and documentation are MIT licensed. The bundled inference notebook is identified separately in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and distributed with the MiniMax Music 3 Community License. That upstream license includes an Acceptable Use Policy and commercial conditions; the project MIT license does not replace it. Model weights are downloaded from Hugging Face at runtime and are not included.

MiniMax Music 3, Google Colab, Hugging Face, Diffusers, Transformers, OpenCC, and SGLang-Omni remain third-party projects and services. Read their current licenses and terms before using or distributing models, outputs, or hosted services.

## Offline checks

These checks do not provision a Colab session or consume compute units:

```bash
python3 scripts/runner.py --help
python3 -m py_compile scripts/runner.py
bash -n install.sh
```

## Reference

The repository layout and installer are informed by [minimax-h3-colab-skill](https://github.com/killkli/minimax-h3-colab-skill). The workflow and bundled notebook are based on the current local MiniMax Music 3 repository and the [official model documentation](https://huggingface.co/MiniMaxAI/MiniMax-Music3).
