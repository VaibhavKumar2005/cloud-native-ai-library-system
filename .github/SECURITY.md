# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in VeriRAG, please **do not** open a public issue.

Instead, email us at: **security@verirag.dev**

Include:
- Description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact
- Your contact information

We will:
- Acknowledge receipt within 24 hours
- Investigate and confirm the vulnerability
- Develop and test a fix
- Release a patch within 7-14 days
- Credit you in the advisory (optional)

---

## Security Practices

### Authentication & Authorization
- ✅ JWT-based session management
- ✅ Field-level document encryption
- ✅ Vault-backed secret management
- ✅ Multi-tenant isolation per user

### Data Protection
- ✅ Encryption at rest (Fernet cipher, PBKDF2 key derivation)
- ✅ SSL/TLS for all network communication
- ✅ User documents never shared across accounts
- ✅ Audit logging for sensitive operations

### Infrastructure
- ✅ HashiCorp Vault for local development
- ✅ Azure Key Vault for cloud deployment
- ✅ Rate limiting on API endpoints
- ✅ CORS properly configured

### Development
- ✅ Dependency vulnerability scanning (Dependabot)
- ✅ Security testing in CI/CD
- ✅ Code review for all changes
- ✅ Regular security audits

---

## Supported Versions

| Version | Status | Support Until |
|---------|--------|---------------|
| 1.0.x | Current | Nov 2026 |
| 0.9.x | EOL | Apr 2025 |

---

## Security Updates

We release security patches as soon as they're tested. Always keep VeriRAG updated to the latest patch version.

Monitor releases here: [Releases](https://github.com/VaibhavKumar2005/cloud-native-ai-library-system/releases)

---

## Questions?

For security concerns about features or deployment:
- Open a discussion → [GitHub Discussions](https://github.com/VaibhavKumar2005/cloud-native-ai-library-system/discussions)
- Email → security@verirag.dev

---

**Last updated:** April 2025
