import threading
import sounddevice as sd
from kokoro import KPipeline


# -------------------------
# Config — change voice here
# -------------------------
VOICE       = "am_michael"  # options: *af_heart, af_bella, af_sarah, *am_adam, am_michael
LANG_CODE   = "a"         # "a" = American English, "b" = British English
SAMPLE_RATE = 24000


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

            with sd.OutputStream(
                samplerate=SAMPLE_RATE,
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

                    chunk_duration = len(audio) / SAMPLE_RATE
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