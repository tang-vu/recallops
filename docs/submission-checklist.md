# Submission Checklist

This file prepares evidence but does not authorize submission, publication, upload, or a "ready for judging" state.

## Repository

- [x] Public repository exists with preserved history.
- [x] MIT license is present.
- [x] Source and judge-facing copy are in polished English.
- [x] Prior Work declaration is explicit.
- [x] Production memory reads and writes are linked from the README.
- [ ] Final commit hash is recorded after all quality gates.
- [ ] Repository secret scan is repeated immediately before submission.

## Core Sibyl proof

- [x] Production runtime directly calls `sibyl-memory-client==0.8.0`.
- [x] Session 1 persists a verified failure.
- [x] A separate Session 2 process retrieves it and changes the decision.
- [x] Memory evidence is visible in the receipt.
- [x] Missing or failed memory returns `ESCALATE` and stops commerce.
- [x] Twelve-scenario benchmark artifacts exist in JSON, CSV, and Markdown.
- [x] Deletion test passes.
- [ ] Record the required continuous, unedited fresh-process video segment.

## Product and quality

- [x] Control-plane UI is responsive and keyboard accessible.
- [x] Fixture use is visible.
- [x] Backend, web, browser, contract, and dependency gates are scripted.
- [x] Local Anvil contract and viem interaction are verified.
- [x] Run every `make check` component locally and in GitHub CI; exact results are recorded in `STATUS.md`.
- [x] Verify every local documentation link from a clean clone.
- [ ] Verify the video is 2 to 5 minutes and readable at normal playback speed.

## Partner evidence

- [ ] Review and complete [Issue 1](https://github.com/tang-vu/recallops/issues/1) only with explicit Base Sepolia approval.
- [ ] Review and complete [Issue 2](https://github.com/tang-vu/recallops/issues/2) only with explicit Virtuals live-job approval.
- [ ] Virtuals: real ACP-native job completed with public or judge-verifiable evidence.
- [ ] Base: real Base Sepolia registry deployment verified on the official explorer.
- [ ] Base: real product-triggered receipt anchor verified on the official explorer.
- [ ] Partner claim text matches only evidence actually obtained.

If any partner checkbox remains empty, do not claim that multiplier. Fixture IDs and Anvil hashes are not partner proof.

## Submission fields

- [x] Draft title, short description, long description, video description, build-log post, launch post, and tags are prepared in `docs/submission-draft.md`.
- [x] Private form copy and truthful memory primitive selections are prepared in `docs/submission-form-copy.md`.
- [x] First build-in-public post published with the verified launch visual and recorded status URL.
- [ ] Publish and record the second required build-in-public post.
- [ ] Final repository URL and commit copied into the submission form.
- [ ] Final video URL approved by the builder.
- [ ] All form fields reviewed by Vu Tang.
- [ ] Explicit human approval received to submit.
- [ ] [Issues 3 and 4](https://github.com/tang-vu/recallops/issues) are completed by the builder, not automation.

## Final truth check

- [ ] No fabricated user, interview, pilot, waitlist, revenue, transaction, ACP job, or PMF claim.
- [ ] No secret, private link, wallet material, OTP, or authorization header appears in repository or video.
- [ ] No Base or Virtuals verification badge appears without real evidence.
- [ ] Submission has not been marked ready or sent by automation.
