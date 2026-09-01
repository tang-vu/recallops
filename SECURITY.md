# Security Policy

## Supported versions

RecallOps is an active hackathon build. Only the latest commit on `main` is supported during the build window.

## Reporting a vulnerability

Please open a private security advisory in this GitHub repository. Do not include wallet secrets, database contents, authentication tokens, personal data, or a live exploit against third-party infrastructure in a public issue.

## Safety boundaries

RecallOps fails closed when mandatory memory is unavailable. It never silently swaps Sibyl Memory for another production persistence layer. Live economic actions require an unexpired approval receipt, an allowed network, and explicit integration configuration.

Never commit private keys, seed phrases, API tokens, Sibyl databases, Virtuals credentials, or unredacted private evidence. The receipt registry is designed to hold only non-sensitive digests.
