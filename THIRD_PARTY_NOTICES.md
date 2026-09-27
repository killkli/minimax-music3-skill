# Third-party notices

## MiniMax Music 3 notebook and model

`assets/MiniMax_Music3_Colab.ipynb` packages a Colab/Diffusers inference workflow for the public `MiniMaxAI/MiniMax-Music3` checkpoint. The model, its associated inference software, and its own license terms belong to MiniMax. The complete MiniMax Music 3 Community License is included in [`LICENSE-MINIMAX-MUSIC3.md`](LICENSE-MINIMAX-MUSIC3.md), retrieved from the [official Hugging Face model repository](https://huggingface.co/MiniMaxAI/MiniMax-Music3/blob/main/LICENSE). No model weights or generated audio are included here.

The model license includes an Acceptable Use Policy and commercial conditions. Read the current license before using or distributing the model or outputs; this repository's MIT license does not replace those terms.

## Runtime dependencies

The notebook installs or imports `diffusers`, `transformers`, `accelerate`, `soundfile`, `opencc`, `torch`, and Google Colab runtime modules. The runner uses Python's standard library and invokes `google-colab-cli` as an external command. These packages and services are not vendored here and retain their own licenses and terms.

## Project license scope

The root [`LICENSE`](LICENSE) applies to this repository's original skill instructions, runner, installer, and documentation. The bundled notebook is distributed with the MiniMax Music 3 license notice above. Model weights, Colab, Hugging Face, SGLang-Omni, and generated audio are outside this project's MIT license.
