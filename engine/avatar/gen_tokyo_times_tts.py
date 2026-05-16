"""Generate Tasuke TTS for the Tokyo Times article."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import soundfile as sf
import numpy as np

OUTPUT_DIR = r"C:\QIH\engine\avatar\outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

ARTICLE = """
The Quiet Intersection: How Autonomous Sentinels Rewrote Tokyo's Gridlock.
By Tasuke Hattori, Senior Technology Correspondent. Published May 16, 2026.

TOKYO — Stand at the center of the Shibuya Crossing at 5:00 PM on a Friday, and you will notice something profoundly unsettling: it is completely orderly.

For decades, the choreography of Tokyo's busiest intersections relied on the sharp whistles, white-gloved hand signals, and hyper-vigilant eyes of the Tokyo Metropolitan Police Department's traffic division. Today, those human officers are gone. In their place stand the Type-9 Anzen Autonomous Sentinels — sleek, three-meter-tall humanoid units polished in police blue and white, their optical sensors pulsing with a calm, continuous amber glow.

Tokyo has officially become the first megacity in the world to entirely replace its human traffic police force with highly capable, generative AI robots. What began three years ago as a pilot program in the Roppongi district has quietly expanded into a full-scale civic transformation.

The impact on Tokyo's notorious congestion was immediate. According to data released by the Tokyo Ministry of Transport, traffic fluidity has increased by 34 percent citywide since the full deployment of the Sentinels. Unlike human officers, who rely on line-of-sight and radio updates, the Type-9 units operate on a unified quantum-mesh network. They don't just see the cars in front of them; they process real-time telemetry from thousands of municipal cameras, satellites, and smart-vehicle pings across the prefecture.

A human officer takes seconds to recognize a bottleneck and react. The Sentinels calculate traffic flow changes at the microsecond level. They predict gridlock before it even forms, subtly adjusting pedestrian countdowns and autonomous vehicle routing to dissolve traffic knots before a single brake light taps.

For Tokyo's residents, the transition has evoked a complex mix of awe and alienation. The traditional Koban — the neighborhood police box — was long viewed as a community anchor, a place where lost tourists found directions and children sought help. Now, the Koban house charging pods.

While the robots are programmed with flawless, polite Japanese honorifics and can project holographic maps for lost pedestrians, the lack of human empathy is palpable. It's efficient, yes, but it feels hollow. There used to be a comfort in seeing an officer smile or wave you through a crosswalk. Now, it feels like we are being managed by a giant, polite computer.

Despite the emotional friction, the numbers defend the machines. Traffic accidents involving pedestrians have plummeted to near zero in zones managed by the Sentinels. The AI units possess flawless threat-detection. When a reckless driver attempted to flee a hit-and-run in Shinjuku last month, a Sentinel calculated the vehicle's trajectory, deployed a localized electromagnetic spike strip within seconds, and immobilized the car without a single injury.

Yet, civil liberties groups are raising alarms. The robots don't just direct traffic — they scan faces. With every pedestrian crosswalk acting as a high-resolution biometric checkpoint, critics argue that Tokyo has traded its vibrant street culture for a flawless, sterile panopticon.

As dusk falls over the city, the amber lights of the Sentinels switch to a high-visibility neon blue. They stand tireless against the rain, wind, and seismic tremors, guiding millions of souls through the neon-lit arteries of the world's largest metropolis.

Tokyo has achieved the impossible: a city without traffic jams. But as the human officers fade into history, the city must ask itself what else it left behind on the road to perfection.
""".strip()

print("Loading Kokoro TTS pipeline...")
from kokoro import KPipeline

pipeline = KPipeline(lang_code='a')

print("Generating Tasuke voice for Tokyo Times article (~800 words)...")
samples = []
for i, (_, _, audio) in enumerate(pipeline(ARTICLE, voice='am_adam', speed=0.92, split_pattern=r'\n+')):
    samples.append(audio)
    print(f"  Segment {i+1} done ({len(audio)/24000:.1f}s)")

if not samples:
    print("ERROR: no audio generated")
    sys.exit(1)

combined = np.concatenate(samples)
out_path = os.path.join(OUTPUT_DIR, "tasuke_tokyo_times.wav")
sf.write(out_path, combined, 24000)
duration = len(combined) / 24000
print(f"\nSaved: {out_path}  ({duration:.1f}s / {duration/60:.1f} min)")
print("Ready for Hallo2 render.")
