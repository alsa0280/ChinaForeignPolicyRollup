"""AI processing service (Role 4) for the China Foreign Policy Roll-up.

Receives one cleaned article (a ``document``) and returns one ``ai_claims`` row:
English title and summary, focus area, relevance and credibility scores, and
claims that are validated against the source text. Uses a local Ollama model.
"""
