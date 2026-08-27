import threading
import sounddevice as sd
from kokoro import KPipeline
from scipy.signal import resample_poly
from fractions import Fraction


# -------------------------
# Config — change voice here
# -------------------------
VOICE       = "am_heart"  # options: *af_heart, af_bella, af_sarah, *am_adam, am_michael
LANG_CODE   = "a"         # "a" = American English, "b" = British English
SAMPLE_RATE = 24000

# -------------------------
# Output device selection
# -------------------------
TARGET_BT_DEVICE_NAME = "ARCN speaker"

# -------------------------
# Global audio lock
# Prevents the assistant loop and proactive engine
# from opening the audio device simultaneously.
# Any call to speak() blocks until the current one finishes.
# -------------------------
_audio_lock = threading.Lock()

# -------------------------
# Mute state — Task 1 (Arcn mute).
# _mute_event: Event, not a plain bool — needs to be safely
# readable from the audio-writing thread while being set/cleared
# from the hotkey (AppKit event) thread.
#
# _pending_restate_text: only ever holds text when a speak() call
# got cut off MID-STREAM by mute. NOT set when a call is suppressed
# before it starts (already muted when called) and NOT set when a
# call finishes naturally — restate-on-unmute is one-shot and only
# fires for a genuine mid-sentence interruption, per spec. Any
# newer speak() activity invalidates a pending one as stale.
# -------------------------
_mute_event           = threading.Event()
_pending_restate_text  = None
_restate_lock          = threading.Lock()


def is_muted() -> bool:
    return _mute_event.is_set()


def mute():
    """Sets the mute flag. Cheap — just flips an Event, safe to call
    directly from the hotkey handler without spawning a thread."""
    _mute_event.set()
    print("Arcn: muted")


def unmute():
    """Clears the mute flag. Restates ONLY if the last speak() call
    was genuinely interrupted mid-sentence by mute — a preemptive
    mute with nothing playing produces nothing to restate.
    Blocks on speak() when it does restate — call from a background
    thread, not directly from the AppKit event handler."""
    global _pending_restate_text

    _mute_event.clear()
    print("Arcn: unmuted")

    with _restate_lock:
        text = _pending_restate_text
        _pending_restate_text = None  # consume — one-shot, don't restate twice

    if text:
        speak(text)


# -------------------------
# Load Kokoro pipeline once
# at import time — avoids
# reloading on every speak()
# -------------------------
print("Loading Kokoro TTS...")
_pipeline = KPipeline(lang_code=LANG_CODE)
print("  Kokoro ready")



# -------------------------
# Output device selection —
# Prefers the Bluetooth speaker ("Office speaker") when connected.
# Falls back to the Mac's default output device (speakers/headphones)
# if the Bluetooth speaker isn't currently connected — covers using
# Arcn away from the room it's normally in.
# Re-checked on every speak() call since Bluetooth connection state
# can change mid-session — this is a cheap query, not worth caching.
# -------------------------
def _get_output_device():
    try:
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev['name'] == TARGET_BT_DEVICE_NAME and dev['max_output_channels'] > 0:
                return i
    except Exception as e:
        print(f"[speaker] device query failed: {e}")

    # Not found / not connected — None tells sounddevice to use
    # the system default output (Mac speakers or whatever's active)
    return None

# -------------------------
# Determine target sample rate —
# queries the ACTUAL output device's native rate instead of
# assuming Kokoro's 24000Hz will play cleanly everywhere.
# Bluetooth in particular won't tolerate a mismatch gracefully —
# it produces the cracking/distortion we heard on the ARCN speaker.
# -------------------------
def _get_target_samplerate(device):
    try:
        if device is None:
            device = sd.default.device[1]  # resolve system default output index
        info = sd.query_devices(device)
        return int(info['default_samplerate'])
    except Exception as e:
        print(f"[speaker] samplerate query failed: {e}")
        return SAMPLE_RATE  # fall back to Kokoro's native rate — no resampling occurs

# -------------------------
# Public speak function
# ...rest of the docstring

# -------------------------
# Public speak function
#
# bypass_mute: for proactive alerts that must speak even while
# muted (e.g. a timer going off) — Task 1 spec explicitly calls
# this out as an exception, not a general override. Use sparingly.
# -------------------------
def speak(text: str, bypass_mute: bool = False):

    global _pending_restate_text

    if not text or not text.strip():
        return

    if _mute_event.is_set() and not bypass_mute:
        # Never started — not a mid-sentence interruption, so this
        # is NOT restate-eligible. Also clears any earlier pending
        # restate, since something new happening since then makes
        # that old cutoff stale.
        with _restate_lock:
            _pending_restate_text = None
        print(f"Arcn (muted, not spoken): {text}")
        return

    print(f"Arcn: {text}")

    import numpy as np
    import time

    with _audio_lock:
        try:
            generator = _pipeline(text, voice=VOICE)

            output_device = _get_output_device()
            target_rate = _get_target_samplerate(output_device)

            with sd.OutputStream(
                device=output_device,
                samplerate=target_rate,
                channels=1,
                dtype="float32"
            ) as stream:

                SUB_BLOCK = 2048  # samples per interrupt-check window — small enough
                                   # to interrupt within a fraction of a second even
                                   # when Kokoro yields one big chunk for short text

                for result in generator:
                    audio = result.output.audio
                    audio = audio.detach().cpu().numpy()
                    audio = np.clip(audio, -1.0, 1.0).astype(np.float32)

                    # Resample from Kokoro's native rate to the device's rate —
                    # skip the work entirely if they already match
                    if target_rate != SAMPLE_RATE:
                        ratio = Fraction(target_rate, SAMPLE_RATE).limit_denominator(1000)
                        audio = resample_poly(audio, ratio.numerator, ratio.denominator).astype(np.float32)
                    

                    chunk_duration = len(audio) / target_rate
                    write_start = time.time()

                    interrupted = False
                    i = 0
                    while i < len(audio):
                        sub = audio[i:i + SUB_BLOCK]

                        if _mute_event.is_set() and not bypass_mute:
                            # Fade this sub-block to silence, write it, then stop —
                            # decrescendo over a fraction of a second instead of a
                            # hard cut, and small enough to actually be reachable
                            # even on short single-chunk utterances.
                            fade = np.linspace(1.0, 0.0, len(sub), dtype=np.float32)
                            stream.write(sub * fade)
                            interrupted = True
                            break

                        stream.write(sub)
                        i += SUB_BLOCK

                    

                    if interrupted:
                        with _restate_lock:
                            _pending_restate_text = text
                        break

                else:
                    # Loop completed without break — finished naturally,
                    # not interrupted, nothing to restate.
                    with _restate_lock:
                        _pending_restate_text = None

        except Exception as e:
            print(f"[speaker] TTS failed: {e}")