# Two speakers, two microphones, real-time

`two_spk_two_mic.py` — plays 2 bandpassed white noise signals (uncorrelated) out of 2 speakers and records 2
microphones through one full-duplex `sounddevice` callback on an ASIO card (tested on ULTRALITE AVB soundcard).


## Requirements

```
pip install sounddevice numpy scipy
```

Windows plus an ASIO driver. `sd.AsioSettings`.

## Setup

Run once, read the `sd.query_devices()` printout, then set:

```python
device      = 15        # index of your card in that list
speakers    = [1, 2]    # ASIO output channels
microphones = [1, 0]    # ASIO input channels
```

These are the card's own channel indices.
