"""Reference helpers for the experimental EXT-CAPNEG v0.2 surface."""

from .profile_composition import (
    COMPOSITION_HASH_DOMAIN,
    COMPOSITION_VERSION,
    canonical_profile_ref_key,
    resolve_profile_composition,
)

__all__ = [
    "COMPOSITION_HASH_DOMAIN",
    "COMPOSITION_VERSION",
    "canonical_profile_ref_key",
    "resolve_profile_composition",
]
