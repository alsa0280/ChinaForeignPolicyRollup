"""Deterministic checks applied to the model output before anything is stored.

A claim is kept only if its opportunity ID exists, its quote appears word for
word in the article, its dimension is in the fixed list, its date is valid and
its quote shares key terms with the opportunity. Scores are clamped to 1-5.
"""
