"""Generate original synthesized audio; no external downloads required."""
import math
from pathlib import Path
import random
import struct
import wave

RATE = 22050
DEST = Path(__file__).resolve().parent / 'assets'

def write(name, values):
    with wave.open(str(DEST / (name + '.wav')), 'wb') as file:
        file.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        file.writeframes(b''.join(struct.pack('<h', int(max(-1, min(1, value))*26000)) for value in values))

def main():
    DEST.mkdir(exist_ok=True)
    rng = random.Random(42)
    write('shoot', [math.sin(2*math.pi*(1100*t-1900*t*t))*0.35*(1-t/0.16) for t in (i/RATE for i in range(int(RATE*0.16)))])
    write('explosion', [(rng.uniform(-1, 1)*0.55+math.sin(i/RATE*2*math.pi*65)*0.3)*(1-i/(RATE*0.5))**2 for i in range(int(RATE*0.5))])
    write('hit', [math.sin(2*math.pi*135*i/RATE)*0.45*(1-i/(RATE*0.25)) for i in range(int(RATE*0.25))])
    notes = [220, 261.63, 329.63, 293.66, 196, 246.94, 293.66, 261.63]
    samples = []
    for i in range(RATE*16):
        t = i/RATE
        beat = t % 0.5
        note = notes[int(t/0.5) % len(notes)]
        melody = math.sin(2*math.pi*note*t)*math.exp(-beat*7)*0.19
        bass = math.sin(2*math.pi*notes[int(t/2) % len(notes)]/2*t)*0.11
        kick = math.sin(2*math.pi*55*beat)*math.exp(-beat*24)*0.17
        samples.append((melody+bass+kick)*min(1, t*10, (16-t)*10))
    write('music', samples)

if __name__ == '__main__':
    main()
