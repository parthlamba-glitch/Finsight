from .parse_attestation_statement import parse_attestation_statement
from .parse_authenticator_data import parse_authenticator_data
from .structs import AttestationObject
from .parse_cbor import parse_cbor
from .exceptions import InvalidAttestationObjectStructure, InvalidCBORData


def parse_attestation_object(val: bytes) -> AttestationObject:
    """
    Decode and peel apart the CBOR-encoded blob `response.attestationObject` into
    structured data.
    """
    try:
        attestation_dict = parse_cbor(val)
    except InvalidCBORData:
        raise InvalidAttestationObjectStructure("Could not parse attestationObject as CBOR data")

    if type(attestation_dict) is not dict:
        raise InvalidAttestationObjectStructure("attestationObject was not a dict")

    if "fmt" not in attestation_dict:
        raise InvalidAttestationObjectStructure(
            'attestationObject missing required property "fmt"'
        )

    if "authData" not in attestation_dict:
        raise InvalidAttestationObjectStructure(
            'attestationObject missing required property "authData"'
        )

    decoded_attestation_object = AttestationObject(
        fmt=attestation_dict["fmt"],
        auth_data=parse_authenticator_data(attestation_dict["authData"]),
    )

    if "attStmt" in attestation_dict:
        decoded_attestation_object.att_stmt = parse_attestation_statement(
            attestation_dict["attStmt"]
        )

    return decoded_attestation_object
