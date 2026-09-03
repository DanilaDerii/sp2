"""Student pack import helpers."""

__all__ = [
    "ImportedPack",
    "PackImportError",
    "PackValidationError",
    "ValidatedPack",
    "import_pack_zip",
    "validate_pack_directory",
]


def __getattr__(name: str):
    if name in {"ImportedPack", "PackImportError", "import_pack_zip"}:
        from . import pack_importer

        return getattr(pack_importer, name)

    if name in {"PackValidationError", "ValidatedPack", "validate_pack_directory"}:
        from . import pack_validator

        return getattr(pack_validator, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
