# Continuous demo recording / September 9, 2026

A local demo video was recorded from the public RecallOps deployment. It is
prepared for review; it has not been uploaded, posted, or submitted.

## Verified artifact

- Local directory: `.data/demo-recordings/2026-09-08T17-33-28-730Z/`
- MP4: `recallops-demo.mp4`, H.264, 1600 by 900, 25 fps
- Duration: 176.12 seconds (2 minutes 56 seconds)
- Size: 9,581,124 bytes
- Decoded frame count: 4,403
- MP4 SHA-256: `0c77af6e1603a47ff10b1eb812adc5c6e26599b014a89065d08cb5c526366696`
- Original WebM SHA-256: `4adb08603a5efd35e193bd00036d483e82359e75a6103150db370ef867ba30a7`

The original WebM is one continuous Playwright browser recording. Captions and
a real UTC clock were drawn during capture. The MP4 transcodes that recording
without cuts, speed changes, replaced frames, or inserted footage. There is no
audio track; the presentation uses on-screen English captions. Authentication
occurred before opening the recorded page, so workspace keys were never shown.

The recording demonstrates the product home, real workspace evaluation and
owner review, the two-process Sibyl proof, the deterministic benchmark, and the
API guide. Representative frames were inspected for readability, visible
process identity, source linkage, and fixture labels. The MP4 decoded without
reported errors.

## Fresh-process evidence

Both processes reported commit
`4bd74dc2f072dec0d98acfb7d8c593c5df9a1a8a`.

| Evidence | Session 1 | Session 2 |
| --- | --- | --- |
| PID | 61608 | 46704 |
| Session UUID | `b58a4d64-046e-4cb2-beae-a5910dc18ac7` | `ec663e08-b731-4b2a-ac97-18428bbda16e` |
| Started (UTC) | 2026-09-08T17:34:55.557096Z | 2026-09-08T17:35:16.960176Z |
| Outcome | Failed verification persisted, process exited | Same failure recalled, Agent A denied, Agent B approved |

The recalled failure source equals the recorded Session 1 UUID. The UI and
recording script checked this link and the distinct PIDs and UUIDs. The
fresh-process sequence is approximately 1:12 to 2:26 in the continuous video.
The final source-link view is deliberately scrolled above the caption overlay.

Provider deliverables and ACP dispatch are fixtures. Sibyl reads and writes are
real. There is no live job, Base transaction, payment, revenue, or PMF claim.

## Reproduction and quality gates

Use [`scripts/record-demo.mjs`](../../scripts/record-demo.mjs) as documented in
the [script guide](../../scripts/README.md). Each run uses a new request
fingerprint and a new output directory. It never resets the database.

The paired process UI was deployed in `0595364`; recording framing was corrected
in `4bd74dc`. [CI for the recorded commit](https://github.com/tang-vu/recallops/actions/runs/34257822916)
passed all three jobs. The preceding UI release explicitly passed 72 backend
tests and 9 browser tests, with one duplicate mobile process writer skipped;
the proof test separately checks mobile viewport overflow.

A public video URL and the required demo-video post are still pending. Neither
this document nor a local MP4 marks the private build page ready.
