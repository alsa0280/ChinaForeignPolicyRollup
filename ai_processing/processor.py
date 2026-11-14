"""Turns one document into one ai_claims row.

Steps: detect language, trim the text, call the model, validate the output,
compute credibility and build the row. Always returns a row; on any failure
the row has ai_status "failed", the error message and no claims.
"""
