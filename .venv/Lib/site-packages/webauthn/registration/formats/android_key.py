import hashlib
from typing import List, cast

from pyasn1.type.univ import OctetString
from pyasn1.codec.ber.decoder import decode as ber_decode
from pyasn1_modules.rfc5280 import Certificate

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from OpenSSL.crypto import (
    _PublicKey,
    load_certificate,
    dump_certificate,
    FILETYPE_PEM,
    FILETYPE_ASN1,
)

from webauthn.helpers import (
    decode_credential_public_key,
    decoded_public_key_to_cryptography,
    parse_cbor,
    validate_certificate_chain,
    verify_signature,
)
from webauthn.helpers.asn1.android_key import (
    AuthorizationList,
    KeyDescription,
    KeyOrigin,
    KeyPurpose,
)
from webauthn.helpers.exceptions import (
    InvalidCertificateChain,
    InvalidRegistrationResponse,
)
from webauthn.helpers.known_root_certs import (
    google_hardware_attestation_root_2,
    google_hardware_attestation_root_3,
    google_hardware_attestation_root_4,
    google_hardware_attestation_root_5,
)
from webauthn.helpers.structs import AttestationStatement


def verify_android_key(
    *,
    attestation_statement: AttestationStatement,
    attestation_object: bytes,
    client_data_json: bytes,
    credential_public_key: bytes,
    pem_root_certs_bytes: List[bytes],
) -> bool:
    """Verify an "android-key" attestation statement

    See https://www.w3.org/TR/webauthn-2/#sctn-android-key-attestation

    Also referenced: https://source.android.com/docs/security/features/keystore/attestation
    """
    if not attestation_statement.sig:
        raise InvalidRegistrationResponse(
            "Attestation statement was missing signature (Android Key)"
        )

    if not attestation_statement.alg:
        raise InvalidRegistrationResponse(
            "Attestation statement was missing algorithm (Android Key)"
        )

    if not attestation_statement.x5c:
        raise InvalidRegistrationResponse("Attestation statement was missing x5c (Android Key)")

    # x5c includes a root certificate, so break it up accordingly
    x5c_no_root = attestation_statement.x5c[:-1]
    x5c_root_cert = attestation_statement.x5c[-1]

    try:
        x5c_root_cert_openssl = load_certificate(FILETYPE_ASN1, x5c_root_cert)
        x5c_root_cert_pem = dump_certificate(FILETYPE_PEM, x5c_root_cert_openssl)
    except Exception as exc:
        raise InvalidRegistrationResponse(
            "Could not parse x5c root certificate. See __cause__ for more info (Android Key)"
        ) from exc

    # Make sure x509 forms a complete, valid cert chain
    try:
        validate_certificate_chain(
            x5c=x5c_no_root,
            pem_root_certs_bytes=[x5c_root_cert_pem],
        )
    except InvalidCertificateChain as err:
        raise InvalidRegistrationResponse(f"{err} (Android Key)")

    # Make sure the root cert is one of these:
    pem_root_certs_bytes.append(google_hardware_attestation_root_2)
    pem_root_certs_bytes.append(google_hardware_attestation_root_3)
    pem_root_certs_bytes.append(google_hardware_attestation_root_4)
    pem_root_certs_bytes.append(google_hardware_attestation_root_5)

    if x5c_root_cert_pem not in pem_root_certs_bytes:
        raise InvalidRegistrationResponse(
            "x5c root certificate was not a known root certificate (Android Key)"
        )

    # Extract attStmt bytes from attestation_object
    attestation_dict = parse_cbor(attestation_object)
    authenticator_data_bytes = attestation_dict["authData"]

    # Generate a hash of client_data_json
    client_data_hash = hashlib.sha256()
    client_data_hash.update(client_data_json)
    client_data_hash_bytes = client_data_hash.digest()

    verification_data = b"".join(
        [
            authenticator_data_bytes,
            client_data_hash_bytes,
        ]
    )

    # Verify that sig is a valid signature over the concatenation of authenticatorData
    # and clientDataHash using the public key in the first certificate in x5c with the
    # algorithm specified in alg.
    try:
        attestation_cert_bytes = attestation_statement.x5c[0]
        attestation_cert = load_certificate(FILETYPE_ASN1, attestation_cert_bytes)
        attestation_cert_pub_key = attestation_cert.get_pubkey().to_cryptography_key()
        # to_cryptography_key() is of type _Key which includes _PrivateKey types as well. But we
        # know this is the _PublicKey subset of _Key so help type checking understand that
        attestation_cert_pub_key = cast(_PublicKey, attestation_cert_pub_key)
    except Exception as exc:
        raise InvalidRegistrationResponse(
            "Could not parse attestation certificate public key. See __cause__ for more info (Android Key)"
        ) from exc

    try:
        verify_signature(
            public_key=attestation_cert_pub_key,
            signature_alg=attestation_statement.alg,
            signature=attestation_statement.sig,
            data=verification_data,
        )
    except InvalidSignature:
        raise InvalidRegistrationResponse(
            "Could not verify attestation statement signature (Android Key)"
        )

    # Verify that the public key in the first certificate in x5c matches the
    # credentialPublicKey in the attestedCredentialData in authenticatorData.
    attestation_cert_pub_key_bytes = attestation_cert_pub_key.public_bytes(
        Encoding.DER,
        PublicFormat.SubjectPublicKeyInfo,
    )
    # Convert our raw public key bytes into the same format cryptography generates for
    # the cert subject key
    decoded_pub_key = decode_credential_public_key(credential_public_key)
    pub_key_crypto = decoded_public_key_to_cryptography(decoded_pub_key)
    pub_key_crypto_bytes = pub_key_crypto.public_bytes(
        Encoding.DER,
        PublicFormat.SubjectPublicKeyInfo,
    )

    if attestation_cert_pub_key_bytes != pub_key_crypto_bytes:
        raise InvalidRegistrationResponse(
            "Certificate public key did not match credential public key (Android Key)"
        )

    attestation_cert_pyasn1, _ = ber_decode(attestation_cert_bytes, asn1Spec=Certificate())
    attestation_cert_exts = attestation_cert_pyasn1["tbsCertificate"]["extensions"]

    # Verify that the attestationChallenge field in the attestation certificate
    # extension data is identical to clientDataHash.
    ext_key_description_oid = "1.3.6.1.4.1.11129.2.1.17"
    ext_key_description = None
    try:
        # OIDs are best compared as tuples, but OIDs read easier as strings, so bridge that here
        _ext_id = tuple(int(comp) for comp in ext_key_description_oid.split("."))

        # Go through each extension and try to find one with a matching OID
        for idx in range(0, len(attestation_cert_exts)):
            extension = attestation_cert_exts.getComponentByPosition(idx)
            if extension["extnID"]._value == _ext_id:
                ext_key_description = extension
                break
    except Exception as exc:
        raise InvalidRegistrationResponse(
            "Certificate extensions could not be parsed. See __cause__ for more info (Android Key)"
        ) from exc

    if not ext_key_description:
        raise InvalidRegistrationResponse(
            f"Certificate missing extension {ext_key_description_oid} (Android Key)"
        )

    # Parse the KeyDescription extension value
    ext_value: OctetString = ext_key_description["extnValue"]
    parsed_ext, trailing_garbage = ber_decode(ext_value, asn1Spec=KeyDescription())
    if trailing_garbage:
        raise InvalidRegistrationResponse(
            f"Extension {ext_key_description_oid} (Android key) has trailing garbage"
        )

    # Verify that the attestationChallenge field in the attestation certificate extension data
    # is identical to clientDataHash.
    attestation_challenge: OctetString = parsed_ext["attestationChallenge"]
    if bytes(attestation_challenge) != client_data_hash_bytes:
        raise InvalidRegistrationResponse(
            "attestationChallenge field was not the same as the hash of clientDataJSON (Android Key)"
        )

    # Verify the following using the appropriate authorization list from the attestation
    # certificate extension data:
    software_enforced: AuthorizationList = parsed_ext["softwareEnforced"]
    tee_enforced: AuthorizationList = parsed_ext["teeEnforced"]

    # The AuthorizationList.allApplications field is not present on either authorization
    # list (softwareEnforced nor teeEnforced), since PublicKeyCredential MUST be scoped
    # to the RP ID.
    if software_enforced["allApplications"].hasValue():
        raise InvalidRegistrationResponse(
            "allApplications field was present in softwareEnforced (Android Key)"
        )

    if tee_enforced["allApplications"].hasValue():
        raise InvalidRegistrationResponse(
            "allApplications field was present in teeEnforced (Android Key)"
        )

    # The value in the AuthorizationList.origin field is equal to KM_ORIGIN_GENERATED.
    origin = tee_enforced["origin"]
    if origin != KeyOrigin.GENERATED.value:
        raise InvalidRegistrationResponse(
            f"teeEnforced.origin {origin} was not {KeyOrigin.GENERATED}"
        )

    # The value in the AuthorizationList.purpose field is equal to KM_PURPOSE_SIGN.
    purpose = tee_enforced["purpose"]
    if purpose != [KeyPurpose.SIGN.value]:
        raise InvalidRegistrationResponse(
            f"teeEnforced.purpose {purpose} was not [{KeyPurpose.SIGN}]"
        )

    return True
