"""Migration registry, ordered by version."""

from src.migrations import m001_baseline, m002_programs

MIGRATIONS = sorted((m001_baseline, m002_programs), key=lambda m: m.VERSION)
