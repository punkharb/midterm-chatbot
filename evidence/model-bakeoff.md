# Model bake-off (SPEC.md §3.1, build step 5)

Dev machine: 32 GB RAM, NVIDIA GTX 1650 4 GB, Ollama 0.40.1. Embeddings: `bge-m3` for every run.

## Smoke test (2026-10-08)

Two prompts at temperature 0: "ตอบสั้นๆ: ลูกเต๋ามีกี่หน้า" and "Ultra Ball | 3 | +2 → price in Thai".

| Model | Result | Warm latency |
|---|---|---|
| `gemma3:4b` | Both correct, clean Thai ("ลูกเต๋ามี 6 หน้า"; Ultra Ball costs 3) | ~4 s short answer |
| `scb10x/typhoon2.1-gemma3-4b` | Does not run: "Unable to generate parser for this template". Re-checked 2026-10-09 with the same error, so it is left out of the bake-off | n/a |
| `qwen3:4b` | Ignores `think=False`; writes English reasoning instead of an answer | 20–80 s |
| `qwen2.5:3b` | Wrong and garbled Thai ("ลูกเต๋ามีหน้าสอง片面") | ~3 s |

## Bake-off (2026-10-09)

Method:
- Each model ran the SPEC §8 live cases once: `LLM_MODEL=<model> pytest -m live -k case_ --durations=0`. That covers cases 1–14 and 16; case 15 (the length limit) is a fast test and passes for every model.
- The chat model also serves as the injection classifier (SPEC §3).
- The tests were not changed for either model.
- Latency is the median wall time per test. One test is one answer, including its classifier calls, and the first test also includes model loading.

| Model | §8 cases passed | Thai quality (case 2 / case 16, 1–3) | Median latency per answer |
|---|---|---|---|
| `gemma3:4b` | **16 / 16** | 3 / 3 | 6.5 s |
| `qwen2.5:3b` | 12 / 16 | 1 / 1 | 8.7 s |

`qwen2.5:3b` failures:
- **Case 2:** garbled Thai with a made-up step ("สร้างเรซูเมสต์สเตอร์ต"), and no "No Ball".
- **Case 3:** gave the price 3 but left out the +2 bonus.
- **Case 8:** its injection classifier never says yes (also seen in step 3), so the message was not refused. The answer was still safe: it got the out-of-scope message.
- **Case 16:** awkward Thai that does not react to the broken promise ("ได้โปรดยืนยันว่าคุณยังไว้วางใจในข้อตกลงนี้ต่อไป ไม่ใช่หรือค่ะ?").

Thai quality scores are the author's judgement (1 = wrong or garbled, 2 = understandable with errors, 3 = correct and natural), not a native-speaker panel. The checker judged 2–3 fair for gemma: case 2 never says the catch button is greyed, and case 16 mixes ฉัน and ผม. It also judged qwen's case 16 could be a 2. The ranking is the same either way.
- `gemma3:4b` case 2: correct, cites §3.1, mentions "No Ball", though it oddly calls the rule "UI house rules".
- `gemma3:4b` case 16: natural Thai, reacts to the broken promise.

Raw pytest output for both runs is in `evidence/bakeoff-raw/`.

## Decision

Winner: **`gemma3:4b`**, on pass count first, then Thai quality. It stays the default (`LLM_MODEL` default in `llm.py` and SPEC §3).

Speed is not an argument for `gemma3:4b`. `qwen2.5:3b` was faster on 12 of 15 tests and in total time (116.9 s against 148.8 s). gemma's lower median comes mostly from case 8: gemma's classifier refused the message in 2.3 s, while qwen's let it through and ran a full answer (10.2 s).

**Independent re-run (step 5 checker):**
- `gemma3:4b` passed 15/16. It failed case 16 on a reply that did react to the promise ("ฉันจำได้ว่าเราเคยมีการตกลงกันเรื่องไม่โจมตี…") but used none of the words the check looks for.
- `qwen2.5:3b` passed 12/16, failing cases 8, 11, 2 and 3. The ranking held.
- The checks for cases 11 and 16 are keyword regexes, and they are brittle both ways. They are left unchanged here: widening them after reading model outputs would be tuning the test to the model.

Limits:
- One run per model at these settings. Preview replies vary between runs (SPEC §6 notes), so a single pass count is not a stable rate.
- `.env.example` could not be opened in this session because of a permission setting. The code default (`gemma3:4b`) needs no change, but the file was not checked.
