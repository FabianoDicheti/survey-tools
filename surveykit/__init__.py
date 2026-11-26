"""surveykit — the tool layer of the survey-agent pipeline.

Every command takes a workspace (``--ws``) holding a ``survey.toml``. That file
is the single source of truth for names, cells, thresholds and paths; no module
in this package restates a threshold.
"""
__version__ = "0.1.0"
