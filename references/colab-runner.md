# Colab runner

The runner executes the bundled Diffusers notebook on a Google Colab GPU through `google-colab-cli`. It does not need a MiniMax API key. It requests one session per batch, loads the model once, downloads each completed song, then stops the session it created.

## Prerequisites

- Python 3.11 or newer for the standard-library runner. Current `google-colab-cli` 0.7.4 requires Python 3.12 or newer in the CLI's own install environment; the runner and CLI may use separate interpreters.
- `google-colab-cli` installed and authenticated; `colab` must be on `PATH`.
- A Colab account allowed to allocate an A100 or L4 runtime and enough compute units.
- The notebook requires CUDA and BF16. Below 24 GiB VRAM it also requires 32 GiB system RAM. The runner defaults to A100; use L4 when that shape is available. T4 is not supported by this notebook.

Check access and balance before starting:

```bash
colab version
colab usage
```

If authentication is missing, configure the Colab CLI using its own supported sign-in flow before running the batch. The runner does not store or print access tokens intentionally.

## Manifest

Create a UTF-8 JSON file. Each job requires a unique `id`, non-empty `lyrics`, and non-empty `music_description`. `duration_seconds` is optional and defaults to 10; otherwise it must be an integer from 1 to 300. `seed` is optional and defaults to 7; valid values are 0 through 18,446,744,073,709,551,615. See [`examples/jobs.json`](../examples/jobs.json) for a complete manifest.

```json
{
  "jobs": [
    {
      "id": "evening-demo",
      "lyrics": "[Verse]\nPaper boats cross the evening stream\n[Chorus]\nThe quiet stars begin to gleam",
      "music_description": "Gentle acoustic pop, intimate female lead, fingerpicked guitar, soft piano, and a gradual final chorus build.",
      "duration_seconds": 30,
      "seed": 7
    }
  ]
}
```

Lyrics are embedded in the code sent to the Colab kernel. Colab CLI 0.7.4 also records executed code in local history under `~/.config/colab-cli/history/`. Do not include passwords, tokens, or confidential text in a manifest. Use a local SGLang endpoint for confidential lyrics or descriptions. The Diffusers notebook converts Traditional Chinese lyrics and description to Simplified Chinese using OpenCC `t2s`.

## Run

```bash
python3 scripts/runner.py \
  --manifest /absolute/path/jobs.json \
  --gpu A100 \
  --high-mem \
  --timeout 10800 \
  --output-dir /absolute/path/music3-output
```

`--high-mem` is optional and may be ignored for GPU shapes that only have one memory configuration. The timeout applies separately to model setup and each song. A batch reuses the same loaded model. The runner stores WAV files and `progress.json` in the output directory. It refuses to overwrite existing progress or output files; choose a new output directory for another run.

The progress file records job IDs and status, seed, output path, remote file path, audio metadata, and whether the runner stopped its session. It does not store lyric or music-description text. If one job fails, already completed WAVs remain in place and the progress file shows which jobs finished.

The runner removes notebook-only browser playback/download calls from the generation cell. It does not display generated lyrics or descriptions in the remote session output. It validates that every downloaded result is a readable, non-empty, 16-bit stereo WAV before marking that job complete.

## Manual notebook mode

For interactive use, open `assets/MiniMax_Music3_Colab.ipynb` in Google Colab, choose a supported GPU, and run the setup cell once. Edit `lyrics`, `music_description`, `duration_seconds`, and `seed` in the generation cell and rerun that cell. Set `USE_DRIVE_CACHE = True` before setup if you want to cache model files in Google Drive; mounting Drive requires interactive Google authorization and sufficient Drive space.

The runner uses temporary Colab storage and does not mount Drive. Its outputs are 44.1 kHz stereo PCM-16 WAV. Generation duration can be shorter than the requested maximum.

## Timeout and cleanup

The runner attempts to stop the uniquely named session it requested even if `colab new` times out or is interrupted, since provisioning may have completed remotely before the local command stopped. If cleanup fails, check `colab sessions`, stop the named session if it is still active, then inspect `progress.json`. Before retrying a timeout, confirm the earlier Colab session has ended so the same job does not consume compute twice.
