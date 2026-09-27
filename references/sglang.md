# SGLang-Omni endpoint

Use this route only when the user has an SGLang-Omni Music 3 server already running or explicitly asks to set one up. Do not allocate or launch a GPU server without a generation request and a clear target environment.

The current MiniMax Music 3 repository example sends a non-streaming WAV request to `/v1/audio/speech`:

```bash
curl http://127.0.0.1:8000/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "minimax_ttm",
    "input": "[Verse]\nMorning light filtering through the pine\n[Chorus]\nSoftly the world begins to breathe",
    "instructions": "A warm acoustic pop song with intimate female vocals, fingerpicked guitar, soft piano, and a gradual emotional build into a wide final chorus.",
    "response_format": "wav",
    "seed": 7,
    "max_new_tokens": 9000,
    "stream": false
  }' \
  --output minimax_music3.wav
```

Map the user's lyrics to `input`, music description to `instructions`, and requested seed to `seed`. Keep section tags on their own lines. The local repository example uses the model identifier `minimax_ttm`; use the identifier expected by the installed server if it differs. Confirm the endpoint's current request schema when a server version rejects a field.

`max_new_tokens` is an output limit, not an exact duration guarantee. Do not add a `duration_seconds` field unless the installed server documents it. The current repo describes this response as 32 kHz stereo WAV. Inspect the downloaded file's WAV header and report the actual sample rate, channel count, and duration.

This path passes text through unchanged; it does not apply the Colab notebook's Traditional-to-Simplified Chinese conversion. The local server's model, CUDA, and GPU requirements depend on the SGLang-Omni version and configuration. The skill does not assume a server is running just because the API example uses localhost.
