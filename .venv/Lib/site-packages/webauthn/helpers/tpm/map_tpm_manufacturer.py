from .structs import TPM_MANUFACTURERS, TPMManufacturerInfo


def map_tpm_manufacturer_id(id: str) -> TPMManufacturerInfo:
    """
    Map a TPM manufacturer's hex ID to a manufacturer's assigned name and ASCII identifier. IDs
    will be normalized to all-uppercase before attempting to look up a manufacturer.

    Args:
        - `id`: A TPM manufacturer ID string like `"id:FFFFFFFF"`
          (a.k.a. oid "2.23.133.2.1" in SubjectAlternativeName extension)

    Returns:
        An instance of `TPMManufacturerInfo`

    Raises:
        `KeyError` on unrecognized TPM manufacturer ID
    """
    # e.g. "id:51434f4d" -> "id:51434f4D"
    normalized_id = f"id:{id[3:].upper()}"
    return TPM_MANUFACTURERS[normalized_id]
