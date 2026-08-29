# Production backend CI/CD

Pushing or merging into `main` runs isolated tests, builds an ARM64 backend
image, publishes immutable commit-SHA and `latest` tags to GHCR, and deploys the
exact SHA tag to Oracle. Vercel continues to deploy the frontend separately.

## GitHub repository secrets

- `OCI_HOST`: Oracle VM hostname or IP address
- `OCI_USER`: SSH user (normally `ubuntu`)
- `OCI_SSH_PRIVATE_KEY`: private key for the deployment user
- `OCI_SSH_PORT`: SSH port (normally `22`)

Application secrets are not GitHub secrets. They remain only in
`/opt/ssjewellery/.env`. In particular, never regenerate or replace
`ENCRYPTION_KEY`; existing encrypted database values depend on it.

For additional protection, configure the GitHub `production` environment with
branch restrictions allowing only `main` (and optional required reviewers).

## VM layout

```text
/opt/ssjewellery/
|-- .env
|-- docker-compose.prod.yml
|-- deploy/
|   |-- current-image.env
|   `-- previous-image.env
`-- uploads/
```

`current-image.env` contains only the deployed image reference:

```env
BACKEND_IMAGE=ghcr.io/<owner>/<repo>:<full-commit-sha>
```

The Compose service reads application secrets from the VM-only `.env`, binds
Gunicorn only to `127.0.0.1:5005`, and mounts uploads from the host. Migrations
run in a one-off container and are not part of application startup.

## One-time Oracle preparation

1. Ensure the deployment user owns the application directories and can run
   Docker. Do not change or remove the existing `.env` or uploads.

   ```bash
   sudo install -d -o ubuntu -g ubuntu /opt/ssjewellery/deploy
   sudo install -d -o 10001 -g 10001 -m 0755 /opt/ssjewellery/uploads
   sudo chown ubuntu:ubuntu /opt/ssjewellery
   test -f /opt/ssjewellery/.env
   docker compose version
   ```

   The backend image deliberately runs as UID/GID `10001`. Keep the uploads
   directory owned by `10001:10001`; otherwise local image uploads fail with a
   permission error. The deployment workflow reasserts this ownership without
   deleting any files.

2. If the GHCR package is private, create a classic GitHub personal access
   token with only `read:packages` (and repository read access if GitHub
   requires it), then log in once as the same VM user used by CI/CD:

   ```bash
   printf '%s' "$GHCR_READ_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
   unset GHCR_READ_TOKEN
   ```

   The token is stored in Docker's VM credential store, never in the
   application `.env`. Public packages do not require this login.

3. Add the four repository secrets, confirm the SSH public key is present in
   the deployment user's `authorized_keys`, and ensure the VM firewall permits
   SSH from GitHub-hosted runners. Keep Nginx proxying to `127.0.0.1:5005`.

4. The workflow uses `ssh-keyscan` to populate a fresh strict `known_hosts`
   file. Before the first run, compare the VM's SSH host-key fingerprint with
   the fingerprint visible in the Actions log/setup environment through a
   trusted Oracle console. For stronger pinning, replace this bootstrap with a
   protected `known_hosts` value maintained by the operator.

## Deployment behavior

The workflow triggers only on pushes to `main`; merging a pull request creates
such a push. It uploads the version-controlled Compose definition but never
checks out or builds source on Oracle. Oracle pulls the exact commit-SHA image.

Before replacing the backend, the workflow pulls the image and runs:

```bash
flask --app backend.app db upgrade
```

using `/opt/ssjewellery/.env`. A migration failure stops deployment and leaves
the running backend unchanged. After migration, the old `current-image.env` is
copied to `previous-image.env`, the new SHA becomes current, and Compose
recreates only `backend`. Health is retried every five seconds for up to three
minutes, followed by a database-backed `/ready` check. Failure prints container
status and the last 200 backend log lines.

Only the isolated CORS unit suite is used as the CI gate. Other repository tests
create or mutate databases, exercise concurrency, or integrate with broader
application state and therefore are intentionally excluded from production CI.

## Rollback

The workflow preserves the prior immutable image reference but does not
automatically roll back. Database migrations may not be backward-compatible,
so blindly starting old application code against a new schema can be unsafe.
Never run an automatic `flask db downgrade`.

After confirming schema compatibility, an operator can roll back only the
application image:

```bash
cd /opt/ssjewellery
cp deploy/current-image.env deploy/failed-image.env
cp deploy/previous-image.env deploy/current-image.env
docker pull "$(sed -n 's/^BACKEND_IMAGE=//p' deploy/current-image.env)"
docker compose --env-file deploy/current-image.env -f docker-compose.prod.yml up -d --no-deps --force-recreate backend
curl --fail http://127.0.0.1:5005/health
curl --fail http://127.0.0.1:5005/ready
```

Normal future deployment requires only merging a pull request into `main` or
running `git push origin main`.
