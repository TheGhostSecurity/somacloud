"""TLS Certificate Authority for Docker Swarm worker nodes.

Generates a CA keypair used to sign:
- Worker Docker server certs (so the app server can talk to them via mutual TLS)
- App server client certs (so the app server can authenticate to workers)
"""
import logging
import os
import uuid
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

logger = logging.getLogger(__name__)

_CA_DIR = None


def _ca_dir():
    global _CA_DIR
    if _CA_DIR is None:
        from django.conf import settings
        _CA_DIR = Path(settings.BASE_DIR) / "ca"
        _CA_DIR.mkdir(parents=True, exist_ok=True)
    return _CA_DIR


def _ca_key_path():
    return _ca_dir() / "ca.key"


def _ca_cert_path():
    return _ca_dir() / "ca.crt"


def ensure_ca():
    """Generate the CA keypair if it doesn't exist. Returns (key_path, cert_path)."""
    key_path = _ca_key_path()
    cert_path = _ca_cert_path()
    if key_path.exists() and cert_path.exists():
        return str(key_path), str(cert_path)

    logger.info("Generating new CA keypair at %s", _ca_dir())
    key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "SomaCloud Docker CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SomaCloud"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(__import__("datetime").datetime.utcnow())
        .not_valid_after(__import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_cert_sign=True, crl_sign=True,
                content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    os.chmod(str(key_path), 0o600)
    return str(key_path), str(cert_path)


def sign_csr(csr_pem: bytes, node_ip: str | None = None) -> bytes:
    """Sign a PEM-encoded CSR with our CA. Returns the signed cert PEM."""
    ensure_ca()
    ca_key = serialization.load_pem_private_key(_ca_key_path().read_bytes(), password=None)
    ca_cert = x509.load_pem_x509_certificate(_ca_cert_path().read_bytes())
    csr = x509.load_pem_x509_csr(csr_pem)
    if not csr.is_signature_valid:
        raise ValueError("CSR signature is invalid")

    san = [x509.DNSName("*")]
    if node_ip:
        san.append(x509.IPAddress(__import__("ipaddress").ip_address(node_ip)))

    cert = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(__import__("datetime").datetime.utcnow())
        .not_valid_after(__import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM)


def get_ca_cert_pem() -> bytes:
    """Return the CA certificate in PEM format."""
    ensure_ca()
    return _ca_cert_path().read_bytes()


def generate_client_cert(name: str, node_ip: str | None = None) -> tuple[str, str]:
    """Generate a client cert for the app server to authenticate to a worker.

    Returns (cert_path, key_path) stored under DOCKER_TLS_CERT_DIR/<name>/.
    Also copies the CA cert as ca.pem so the orchestrator can find all three.
    """
    ensure_ca()
    from django.conf import settings
    node_dir = Path(settings.DOCKER_TLS_CERT_DIR) / name
    node_dir.mkdir(parents=True, exist_ok=True)
    cert_path = node_dir / "cert.pem"
    key_path = node_dir / "key.pem"
    ca_copy = node_dir / "ca.pem"

    # Copy CA cert if missing
    if not ca_copy.exists():
        ca_copy.write_bytes(get_ca_cert_pem())

    if cert_path.exists() and key_path.exists():
        return str(cert_path), str(key_path)

    ca_key = serialization.load_pem_private_key(_ca_key_path().read_bytes(), password=None)
    ca_cert = x509.load_pem_x509_certificate(_ca_cert_path().read_bytes())
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, f"somacloud-client-{name}"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SomaCloud"),
    ])
    san = [x509.DNSName(name)]
    if node_ip:
        san.append(x509.IPAddress(__import__("ipaddress").ip_address(node_ip)))

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(__import__("datetime").datetime.utcnow())
        .not_valid_after(__import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    key_path.write_bytes(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    os.chmod(str(key_path), 0o600)
    return str(cert_path), str(key_path)


def generate_setup_token() -> str:
    """Generate a one-time setup token for node configuration."""
    return uuid.uuid4().hex
