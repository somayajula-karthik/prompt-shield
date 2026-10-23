# Live Demo Script (about 10 minutes)

All inputs are synthetic. Run everything from the repository root.

| Time | Step | Command | What to point out |
|---|---|---|---|
| 0:00 | Tests | `python -m unittest discover tests/` | 45 tests pass in under 0.1 s |
| 0:30 | Checksum | `python -m prompt_shield.cli validate-aadhaar "2679 0377 4206"` then `... "2679 0377 4207"` | Changing one digit is rejected (Verhoeff) |
| 1:30 | Detect | `python -m prompt_shield.cli detect --file data/demo_input.txt` | All five types found, with exact spans and metadata (e.g. PAN holder type `P`) |
| 2:30 | Mask | `python -m prompt_shield.cli mask -i data/demo_input.txt -o demo_masked.txt --vault demo_vault.json` | Surrogates are format-valid. Both PAN mentions get the **same** surrogate |
| 3:30 | Validate surrogate | `python -m prompt_shield.cli validate-aadhaar "<surrogate from step 4>"` | The fake Aadhaar still passes Verhoeff |
| 4:00 | Vault | `python -m prompt_shield.cli inspect-vault --vault demo_vault.json` | Bidirectional map, occurrence count = 2 for the PAN |
| 4:30 | Unmask | `python -m prompt_shield.cli unmask -i demo_masked.txt --vault demo_vault.json -o demo_restored.txt` | Then compare the files (command below): byte-identical |
| 5:30 | Benchmark | `python -m prompt_shield.cli eval` | 50 samples, 64 entities, 0 FP on the 8 distractors |
| 6:30 | Honest failures | `python scripts/failure_probes.py` | Probe 1: reverse mapping misses reformatted surrogates. Probe 3: 9.3% Verhoeff collision rate. Probe 6: names not masked |
| 8:00 | Live change | Add `"jupiter"` to `KNOWN_UPI_HANDLES` in `prompt_shield/detectors/upi.py`, or add a keyword list to fix a probe | Shows I can change the code on the spot |
| 9:00 | Q&A | — | Next steps: normalised reverse mapping, context scoring, NER |

Byte-identity check (PowerShell):

```powershell
python -c "print(open('data/demo_input.txt','rb').read() == open('demo_restored.txt','rb').read())"
```

Cleanup:

```powershell
Remove-Item demo_masked.txt, demo_restored.txt, demo_vault.json
```
