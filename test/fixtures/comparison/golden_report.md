# Nlptutti comparison report

- Schema: `nlptutti.comparison/1.0`
- Evaluator: `nlptutti test-version`
- Items: 2
- Rate mode: `standard`
- Remove punctuation: `true`
- Unicode normalization: `none`
- Paired bootstrap: `0` resamples, seed `42`, confidence `0.950000`

## Systems

| System | CER micro | CER macro | WER micro | WER macro | CRR micro | CRR macro |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.500000 | 0.500000 | 0.500000 | 0.500000 | 0.500000 | 0.500000 |
| candidate | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 |

## Pairwise deltas

Positive CER/WER deltas mean the candidate has a higher error rate. Positive
CRR deltas mean the candidate has a higher recognition rate.

| Baseline | Candidate | Metric | Micro delta | Macro delta | Micro CI |
| --- | --- | --- | ---: | ---: | --- |
| baseline | candidate | CER | -0.500000 | -0.500000 | - |
| baseline | candidate | WER | -0.500000 | -0.500000 | - |
| baseline | candidate | CRR | 0.500000 | 0.500000 | - |

## Keyword and entity summaries

- No keyword or entity evaluation requested.

## Provenance

- IDs SHA-256: `53d7f4a048bd0daee134c84d46a9de1de3d4c71942f740eb4f964d3fccbeecf3`
- References SHA-256: `2166ca7f4990a95faeb9a6b52d9aba4812b82c1667687bf54303ebc42b653e13`
- Privacy: Raw transcripts are excluded; only fingerprints and aggregate results are stored.

## Warnings

- None.
