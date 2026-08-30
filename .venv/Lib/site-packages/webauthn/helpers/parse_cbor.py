from typing import Any

import cbor2

from .byteslike_to_bytes import byteslike_to_bytes
from .exceptions import InvalidCBORData


def parse_cbor(data: bytes) -> Any:
    """
    Attempt to decode CBOR-encoded data.

    Raises:
        `helpers.exceptions.InvalidCBORData` if data cannot be decoded
    """
    try:
        data = byteslike_to_bytes(data)
        """
        Disallowing duplicate keys accounts for a Python-specific quirk that allows key overwrite
        in malicious CBOR, so e.g. {1: "foo", True: "bar"} does not become {1: "bar"}.

        See https://github.com/duo-labs/py_webauthn/issues/265
        """
        to_return = cbor2.loads(data, allow_duplicate_keys=False)
    except Exception as exc:
        raise InvalidCBORData("Could not decode CBOR data. See __cause__ for more info") from exc

    return to_return
