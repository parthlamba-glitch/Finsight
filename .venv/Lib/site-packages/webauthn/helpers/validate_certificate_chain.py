from typing import List, Optional

from OpenSSL.crypto import (
    X509Store,
    X509StoreContext,
    X509StoreContextError,
    load_certificate,
    FILETYPE_ASN1,
)

from .exceptions import InvalidCertificateChain
from .pem_cert_bytes_to_open_ssl_x509 import pem_cert_bytes_to_open_ssl_x509


def validate_certificate_chain(
    *,
    x5c: List[bytes],
    pem_root_certs_bytes: Optional[List[bytes]] = None,
) -> bool:
    """Validate that the certificates in x5c chain back to a known root certificate

    Args:
        `x5c`: X5C certificates from a registration response's attestation statement
        (optional) `pem_root_certs_bytes`: Any additional (PEM-formatted)
        root certificates that may complete the certificate chain

    Raises:
        `helpers.exceptions.InvalidCertificateChain` if chain cannot be validated
    """
    if pem_root_certs_bytes is None or len(pem_root_certs_bytes) < 1:
        # We have no root certs to chain back to, so just pass on validation
        return True

    # Make sure we have at least one certificate to try and link back to a root cert
    if len(x5c) < 1:
        raise InvalidCertificateChain("x5c was empty")

    # Prepare leaf cert
    try:
        leaf_cert_bytes = x5c[0]
        leaf_cert = load_certificate(FILETYPE_ASN1, leaf_cert_bytes)
    except Exception as exc:
        raise InvalidCertificateChain(
            "Could not prepare leaf cert. See __cause__ for more info"
        ) from exc

    # Prepare any intermediate certs
    try:
        # May be an empty array, that's fine
        intermediate_certs_bytes = x5c[1:]
        intermediate_certs = [
            load_certificate(FILETYPE_ASN1, cert) for cert in intermediate_certs_bytes
        ]
    except Exception as exc:
        raise InvalidCertificateChain(
            "Could not prepare intermediate certs. See __cause__ for more info"
        ) from exc

    # Prepare a collection of possible root certificates
    cert_store = _generate_new_cert_store()
    try:
        for cert in pem_root_certs_bytes:
            cert_store.add_cert(pem_cert_bytes_to_open_ssl_x509(cert))
    except Exception as exc:
        raise InvalidCertificateChain(
            "Could not prepare root certs. See __cause__ for more info"
        ) from exc

    # Load certs into a "context" for validation
    context = X509StoreContext(
        store=cert_store,
        certificate=leaf_cert,
        chain=intermediate_certs,
    )

    # Validate the chain (will raise if it can't)
    try:
        context.verify_certificate()
    except X509StoreContextError as exc:
        raise InvalidCertificateChain(
            "Certificate chain could not be validated. See __cause__ for more info"
        ) from exc

    return True


def _generate_new_cert_store() -> X509Store:
    """
    Something that can be patched during testing to return an X509Store instance with its time
    adjusted to some datetime in the past. This allows full certificate validity checks even after
    cert expiration in the real world. See here:

    https://www.pyopenssl.org/en/stable/api/crypto.html#OpenSSL.crypto.X509Store.set_time
    """
    return X509Store()
