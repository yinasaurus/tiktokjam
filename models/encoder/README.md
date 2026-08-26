# Vendored encoder

This directory must contain a **complete** Model2Vec (or ONNX) model: config, tokenizer, weights. Load from this path, never from a repo id (NFR-12).

Keep the directory well under 100 MiB (C-9). Do not use Git LFS.

Until files are present, the agent uses a deterministic hashing encoder so the dense route stays wired for tests. That stand-in is not a production retriever.
