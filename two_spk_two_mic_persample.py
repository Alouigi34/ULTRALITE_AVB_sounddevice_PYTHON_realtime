# -*- coding: utf-8 -*-
"""
Drive 2 speakers, record 2 microphones, one real-time callback.
blocksize = data_length, one working-rate sample per callback.
"""

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
device           = 15
speakers         = [1, 2]      # ASIO output channels
microphones      = [1, 0]      # ASIO input channels

samplerate       = 48000
data_length      = 2
work_rate        = samplerate // data_length     # 24000

duration         = 10          # seconds
out_gain         = 0.3
recording_amplitude = 1

print(sd.query_devices())

# ----------------------------------------------------------------------
# SIGNALS
# ----------------------------------------------------------------------
n = int(duration * work_rate)


def band_limited_noise(fmin, fmax, samples, rate):
    freqs = np.fft.rfftfreq(samples, 1 / rate)
    spec = np.zeros(len(freqs), dtype=complex)
    idx = (freqs >= fmin) & (freqs <= fmax)
    spec[idx] = np.exp(2j * np.pi * np.random.rand(idx.sum()))
    sig = np.fft.irfft(spec, n=samples)
    return sig / np.max(np.abs(sig))


computed_source_signal1 = band_limited_noise(200, 3000, n, work_rate)
computed_source_signal2 = band_limited_noise(200, 3000, n, work_rate)

mic_signals = np.zeros((2, n))

# ----------------------------------------------------------------------
# DEVICE
# ----------------------------------------------------------------------
sd.default.device = device
asio_out = sd.AsioSettings(channel_selectors=speakers)
asio_in = sd.AsioSettings(channel_selectors=microphones)
sd.default.extra_settings = asio_in, asio_out

input_device = sd.default.device
output_device = sd.default.device

# ----------------------------------------------------------------------
# CALLBACK
# ----------------------------------------------------------------------
index = 0


def callback(indata, outdata, frames, time, status):
    global index

    if index >= n:                 # stop cleanly instead of IndexError
        outdata[:] = 0
        raise sd.CallbackStop

    out_1 = computed_source_signal1[index:(index + 1)]
    out_2 = computed_source_signal2[index:(index + 1)]

    ###### Send to speakers:
    outdata[:, 0] = out_gain * out_1
    outdata[:, 1] = out_gain * out_2

    ###### Record mics signals
    mic_signals[0][index] = recording_amplitude * indata[0, 0]
    mic_signals[1][index] = recording_amplitude * indata[0, 1]

    index = index + 1


try:
    with sd.Stream(device=(input_device, output_device), channels=(2, 2),
                   callback=callback, blocksize=data_length,
                   samplerate=samplerate):
        sd.sleep(int(duration * 1000))
except KeyboardInterrupt:
    pass

# ----------------------------------------------------------------------
# SAVE
# ----------------------------------------------------------------------
mic1 = mic_signals[0][:index]
mic2 = mic_signals[1][:index]

print(f"captured {index} / {n} samples ({index / work_rate:.3f} s)")

wavfile.write("mics.wav", work_rate,
              np.column_stack([mic1, mic2]).astype('float32'))
np.save("mic_signals.npy", mic_signals[:, :index])
