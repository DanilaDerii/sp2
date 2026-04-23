import logging
logging.basicConfig()
logging.getLogger("faster_whisper").setLevel(logging.DEBUG)

print("importing...")
from faster_whisper import WhisperModel

model_size = "base"

print("loading model...")
model = WhisperModel(model_size, device="cpu", compute_type="float32")

print("transcribing...")
segments, info = model.transcribe("audio.mp3", beam_size=5)

print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

for segment in segments:
    print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))

