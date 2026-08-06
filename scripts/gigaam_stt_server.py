"""OpenAI-compatible /v1/audio/transcriptions wrapper around GigaAM-Multilingual.

Lets pipecat's existing Speaches STT provider talk to a self-hosted GigaAM
(Russian/Uzbek ASR, MIT) with zero pipecat code changes — just point the
provider's base_url at this server.

Run (on the GPU box):
    pip install "transformers==5.*" "torch==2.10.*" "torchaudio==2.10.*" \
        hydra-core omegaconf fastapi uvicorn python-multipart
    # revision: ctc = 220M (fast), large_ctc = 600M (best accuracy)
    GIGAAM_REVISION=ctc uvicorn scripts.gigaam_stt_server:app --host 0.0.0.0 --port 8001

Point pipecat at it (STT config): provider=speaches,
    base_url=http://<host>:8001/v1, model=gigaam, language=ru  (or uz)

Smoke test (the runnable check — needs a 16-bit WAV sample):
    curl -F file=@sample.wav -F model=gigaam http://localhost:8001/v1/audio/transcriptions
    # -> {"text": "..."}
"""

import io
import os
import tempfile

import torch
import torchaudio
from fastapi import FastAPI, UploadFile
from transformers import AutoModel

app = FastAPI()

_device = "cuda" if torch.cuda.is_available() else "cpu"
_model = (
    AutoModel.from_pretrained(
        "ai-sage/GigaAM-Multilingual",
        revision=os.getenv("GIGAAM_REVISION", "ctc"),
        trust_remote_code=True,  # GigaAM ships its inference code in the repo
    )
    .eval()
    .to(_device)
)


@app.post("/v1/audio/transcriptions")
def transcriptions(file: UploadFile):
    # pipecat's SegmentedSTTService already sends a complete-utterance WAV;
    # extra form fields (model, language) are ignored — GigaAM auto-detects
    # language across 70+ langs. Conformer wants 16 kHz mono, and telephony
    # audio is often 8 kHz, so resample.
    wav, sr = torchaudio.load(io.BytesIO(file.file.read()))
    if wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)
    if sr != 16000:
        wav = torchaudio.functional.resample(wav, sr, 16000)
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        torchaudio.save(tmp.name, wav, 16000)
        with torch.inference_mode():
            result = _model.transcribe(tmp.name)
    # transcribe() returns str (some variants return list[str]); normalize.
    text = " ".join(result) if isinstance(result, (list, tuple)) else str(result)
    return {"text": text.strip()}
