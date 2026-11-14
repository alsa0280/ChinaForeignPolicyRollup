"""Two-part credibility score.

Part 1 (rule): base score from the source type in source_registry.json
(official 4, company 3, reported 3, unknown 2).
Part 2 (model): an adjustment of -1, 0 or +1 with a stated reason.
The final score is clamped to 1-5 and explained in credibility_reason.
"""
