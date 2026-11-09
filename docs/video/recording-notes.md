# MVP demo recording

The video demonstrates PromiseOps on source commit `1e70c7947e290827a922e4e83fb6940535a4e3fe`, using a separate local demo database and fictional data.

- Duration: 323.594 seconds (5:23).
- Picture: native 1920 × 1080, H.264, 12 fps.
- Sound: English narration, AAC; generated locally with Kokoro ONNX, voice `af_heart`.
- Captions: burned into the video; matching `MVP.srt` is included.
- Recording: TIA Story compiler, player and CDP; 31 playback steps completed, no drift or capture errors, 8 highlight regions found.

The edit shows each action before holding its observed result during the explanation. Frames come from the same recorded run. Opening, changes, architecture and closing cards accompany their respective narration.

Verification covered full-file FFmpeg decoding, codec/dimensions/duration, non-silent finite narration audio and representative frame review. A teammate review of the full video and narration remains requested before submission.

The demo shows 93.3% on time with intervention and 86.7% without intervention. EUR 25 is the stated Round 1 business-case assumption; EUR 10 is the intervention cost recorded in the demo. This is a simulated comparison, not a measured production saving.

TTS sources: [Kokoro ONNX](https://github.com/thewh1teagle/kokoro-onnx) (MIT runtime), [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (Apache-2.0 weights).
