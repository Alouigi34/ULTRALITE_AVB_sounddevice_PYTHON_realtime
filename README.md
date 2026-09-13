# Two speakers, two microphones, real-time

`two_spk_two_mic.py` — plays 2 signals out of 2 speakers and records 2
microphones through one full-duplex `sounddevice` callback on an ASIO card.

Structure is the same as the WFS reproduction loop it came from:
`blocksize = data_length`, one working-rate sample handled per callback. The
card runs at `samplerate` (48 kHz), the signal chain runs at
`samplerate / data_length` (24 kHz), and each output sample is held across the
whole block.

## Requirements

```
pip install sounddevice numpy scipy
```

Windows plus an ASIO driver. `sd.AsioSettings` does not exist on macOS or Linux.

## Setup

Run once, read the `sd.query_devices()` printout, then set:

```python
device      = 15        # index of your card in that list
speakers    = [1, 2]    # ASIO output channels
microphones = [1, 0]    # ASIO input channels
```

These are the card's own channel indices, not positions in the stream.
`microphones = [1, 0]` swaps which physical input lands in `mic_signals[0]` —
check it before trusting any left/right result.

- `samplerate` must match the ASIO control panel or the stream won't open.
- `data_length` is blocksize and decimation factor at once; changing it changes
  `work_rate`, and everything downstream must use `work_rate`.
- `out_gain` — `outdata` is float32 in [-1, 1], anything past that clips.
- `duration` sizes the buffers, so the stream stops when the signal runs out.

## Signals

`computed_source_signal1` / `2` are band-limited noise, 200–3000 Hz, generated
at `work_rate`. Swap in your own arrays of length `n`.

## Output

- `mics.wav` — two mic channels at `work_rate`
- `mic_signals.npy` — raw floats, shape `(2, index)`

## Notes

**Let the card settle.** The original slept 6–8 s before each stream. If you
loop over several measurements, put a `time.sleep(4)` between them rather than
opening streams back to back — that is what keeps recorded lengths consistent
run to run.

**Recorded length** is `index`, exactly. No `np.max(np.nonzero(...))` trimming
needed, which is good, because that silently truncates when the signal ends
near zero.

**The index guard** (`if index >= n`) is the one thing added to the original
callback. Without it, one callback past the buffer raises `IndexError` inside
the callback, PortAudio aborts the stream, and you get a short recording with
no obvious cause. Remove it if you want the original behaviour back.

**Latency is not compensated.** The mic sample read in callback *n* is not the
response to what was sent in callback *n* — converter round trip plus time of
flight sit in between. For impulse responses or ITD work, cross-correlate
against the source arrays to find the real offset.

**Aliasing.** `indata[0, 0]` keeps 1 of every 2 frames with no lowpass, so
content above 12 kHz folds back into the band; the zero-order hold on output
puts an image near 24 kHz. With a 3 kHz working band neither is fatal, but both
show up at the top of any spectrum you compute.
