# Casper Ombre production bundle

This directory is the C2 static deployment design for:

- repository: https://github.com/Yinglianchun/Ombre-Brain.git
- branch: main
- source SHA: 284c9c7b0e51a0ba0032c7028f705d72458cb304

It defines two isolated services, one shared Casper data/state boundary, and no
real credentials. It has not been built, started, or tested against any remote
API.

Important entry points:

- compose.yaml: isolated Brain and Gateway services
- config/config.yaml: conservative, secret-free production baseline
- env/casper.env.example: variable names only
- manifest.yaml: frozen namespace and policy
- scripts/preflight.sh: read-only VPS preflight for the next stage
- scripts/healthcheck.sh: read-only service health probes
- docs/DEPLOYMENT.md: design and unresolved acceptance gates
- docs/SECRET-INVENTORY.md: credential consumers and rotation impact
- docs/ROLLBACK.md: paired data/state rollback design
- docs/STATIC-ACCEPTANCE.md: C2 validation record

The bundle is not production-ready until every item under
BLOCKING_USER_CONFIGURATION in docs/DEPLOYMENT.md is resolved and verified in a
separately authorized stage.
