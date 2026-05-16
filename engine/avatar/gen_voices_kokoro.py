"""Generate voice samples for Tasuke and Maia using Kokoro TTS (Apache 2.0, no auth)."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import soundfile as sf
import numpy as np

OUTPUT_DIR = r"C:\QIH\engine\avatar\outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Loading Kokoro TTS pipeline...")
from kokoro import KPipeline

# am_adam = deep male American English
# af_sarah = warm female American English
# af_bella = expressive female
# am_michael = calm male

VOICES = {
    "tasuke": {
        "voice": "am_adam",
        "text": (
            "Hello, I am Tasuke Hattori, your strategic intelligence partner at Quiddity Innovations. "
            "I specialize in analysis, planning, and delivering precise insights to help you move forward with confidence. "
            "How may I assist you today?"
        ),
        "output": "tasuke_voice.wav",
        "desc": "Deep calm male - am_adam"
    },
    "maia": {
        "voice": "af_sarah",
        "text": (
            "Hi there! I'm Maia, your AI assistant from Quiddity Innovations. "
            "I'm here to help you think through problems, create content, and get things done efficiently. "
            "It's great to meet you — what shall we work on together?"
        ),
        "output": "maia_voice.wav",
        "desc": "Warm expressive female - af_sarah"
    }
}

for agent, config in VOICES.items():
    print(f"\n[{agent.upper()}] Generating voice: {config['desc']}...")
    pipeline = KPipeline(lang_code='a')  # 'a' = American English

    samples = []
    for _, _, audio in pipeline(config['text'], voice=config['voice'], speed=0.95, split_pattern=r'\n+'):
        samples.append(audio)

    if samples:
        combined = np.concatenate(samples)
        out_path = os.path.join(OUTPUT_DIR, config['output'])
        sf.write(out_path, combined, 24000)
        duration = len(combined) / 24000
        print(f"  Saved: {out_path}  ({duration:.1f}s)")
    else:
        print(f"  ERROR: no audio generated for {agent}")

print("\n=== Voice generation complete ===")
print(f"Output folder: {OUTPUT_DIR}")
