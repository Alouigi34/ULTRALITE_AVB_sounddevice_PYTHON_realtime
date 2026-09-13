# -*- coding: utf-8 -*-

import threading
import numpy as np
import sounddevice as sd
from scipy.io import wavfile

# ----------------------------------------------------------------------
DEVICE           = 15
SPEAKER_CHANNELS = [1, 2]
MIC_CHANNELS     = [1, 0]
USE_ASIO         = True

SAMPLERATE       = 48000
DATA_LENGTH      = 2                       # blocksize, and the decimation factor
WORK_RATE        = SAMPLERATE // DATA_LENGTH   # 24000
DURATION         = 10.0

OUT_GAIN         = 0.3
REC_AMPLITUDE    = 1.0
# ----------------------------------------------------------------------

print(sd.query_devices())

n_work = int(DURATION * WORK_RATE)         


def band_limited_noise(fmin, fmax, samples, rate):
    freqs = np.fft.rfftfreq(samples, 1 / rate)
    spec = np.zeros(len(freqs), dtype=complex)
    idx = (freqs >= fmin) & (freqs <= fmax)
    spec[idx] = np.exp(2j * np.pi * np.random.rand(idx.sum()))
    sig = np.fft.irfft(spec, n=samples)
    return sig / np.max(np.abs(sig))


source_1 = band_limited_noise(200, 3000, n_work, WORK_RATE)
source_2 = band_limited_noise(200, 3000, n_work, WORK_RATE)

mic_signals = np.zeros((2, n_work))

if USE_ASIO:
    sd.default.device = DEVICE
    sd.default.extra_settings = (sd.AsioSettings(channel_selectors=MIC_CHANNELS),
                                 sd.AsioSettings(channel_selectors=SPEAKER_CHANNELS))

index = 0
overrun_hits = 0


def callback(indata, outdata, frames, time_info, status):
    """One working-rate sample per call. outdata is held for DATA_LENGTH frames."""
    global index, overrun_hits

    if status:
        print(status, flush=True)

    # --- the guard the original was missing: never index past the buffer
    if index >= n_work:
        outdata[:] = 0
        raise sd.CallbackStop

    # send to speakers (zero-order hold across the whole block)
    outdata[:, 0] = OUT_GAIN * source_1[index]
    outdata[:, 1] = OUT_GAIN * source_2[index]

    # record: mean over the block instead of indata[0], a crude but real
    # anti-alias filter. Use indata[0, :] instead to match the original exactly.
    mic_signals[0][index] = REC_AMPLITUDE * indata[:, 0].mean()
    mic_signals[1][index] = REC_AMPLITUDE * indata[:, 1].mean()

    index += 1


done = threading.Event()

try:
    with sd.Stream(device=(DEVICE, DEVICE),
                   channels=(2, 2),
                   samplerate=SAMPLERATE,
                   blocksize=DATA_LENGTH,
                   dtype='float32',
                   callback=callback,
                   finished_callback=done.set) as stream:
        print(f"working rate {WORK_RATE} Hz, "
              f"latency {stream.latency[0]*1000:.1f}/{stream.latency[1]*1000:.1f} ms")
        done.wait(timeout=DURATION + 5)
except KeyboardInterrupt:
    pass

# `index` is the exact length - no np.nonzero() guessing needed
n = index
print(f"captured {n} / {n_work} samples ({n / WORK_RATE:.3f} s)")
if n < n_work:
    print("WARNING: stream ended early - check for xruns above")

mic_1 = mic_signals[0][:n]
mic_2 = mic_signals[1][:n]

wavfile.write("mics_persample.wav",
              WORK_RATE,
              np.column_stack([mic_1, mic_2]).astype('float32'))
np.save("mic_signals_persample.npy", mic_signals[:, :n])
