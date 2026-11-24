# Local development: Keycloak with Docker

This guide runs Keycloak on your machine with Docker so you can sign in and call the API locally.
The realm, clients, roles and test users are imported from
[`keycloak/realm-export.json`](../keycloak/realm-export.json) each time the container starts.

> **Dev only.** This setup uses Keycloak `start-dev`, an in-container H2 database, the
> `admin`/`admin` console login, a password-grant client and test users with known passwords.
> Don't use any of it in production.

## 1. Prerequisites

- Docker Desktop running (Compose v2: `docker compose version`)
- Port **8080** free on your machine (Keycloak HTTP)

The Compose service uses `quay.io/keycloak/keycloak:26.8.2` and publishes the port as
`127.0.0.1:8080:8080`. Keycloak is therefore reachable only from your own machine, not from other
devices on your network. Containers on the same Compose network (API, worker, Newman) still reach
it at `http://keycloak:8080`.
- The API's Python environment set up as described in the [README](../README.md)

## 2. Start Keycloak

From the repository root:

```powershell
docker compose -f docker-compose.postman.yml up -d keycloak
```

Naming the `keycloak` service starts only Keycloak, not Postgres, Redis, the API or Newman. The
first start takes about 30–60 s. Check that it is ready:

```powershell
docker compose -f docker-compose.postman.yml ps keycloak
```

The `STATUS` column should show `healthy`. Check that the realm was imported:

```powershell
docker compose -f docker-compose.postman.yml logs keycloak | Select-String "imported|Import finished"
```

You should see `Realm 'job-process' imported` and `Import finished successfully`.

## 3. What you get

| Item | Value |
|---|---|
| Admin console | <http://localhost:8080/admin> (user `admin`, password `admin`) |
| Realm | `job-process` |
| Issuer | `http://localhost:8080/realms/job-process` |
| OIDC discovery | <http://localhost:8080/realms/job-process/.well-known/openid-configuration> |
| JWKS | <http://localhost:8080/realms/job-process/protocol/openid-connect/certs> |
| Account / self-registration | <http://localhost:8080/realms/job-process/account> |

**Clients**

| Client ID | Type | Use |
|---|---|---|
| `job-process-api` | bearer-only | The API itself; the value required in the token `aud` claim |
| `job-process-web` | public, Authorization Code + PKCE (S256) | Front-end SPA (redirects allowed for `localhost:4200`, `localhost:5173` and Swagger UI) |
| `job-process-dev` | public, direct access (password) grant | Scripts, Postman, quick manual testing. **Dev only** |

The `job-process-web` and `job-process-dev` clients include an audience mapper that adds
`job-process-api` to `aud`.

**Users**

| Email / username | Password | Realm roles |
|---|---|---|
| `candidate@example.com` | `DevPassword123!` | `user` |
| `admin@example.com` | `DevAdminPassword123!` | `user`, `admin` |

## 4. Point the API at Keycloak

In your `.env` (copied from `.env.example`):

```dotenv
KEYCLOAK_SERVER_URL=http://localhost:8080
KEYCLOAK_REALM=job-process
KEYCLOAK_AUDIENCE=job-process-api
KEYCLOAK_ADMIN_ROLE=admin
```

These are also the defaults, so you can leave them out. Then start the API as usual:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

> **Use the same host name everywhere.** The API checks that the token's `iss` claim equals
> `KEYCLOAK_SERVER_URL/realms/KEYCLOAK_REALM`. Keycloak in dev mode builds `iss` from the URL
> you requested the token from. A token fetched from `http://127.0.0.1:8080` is therefore
> rejected by an API configured with `http://localhost:8080`, and the other way round.

## 5. Get a token and call the API

```powershell
$token = (Invoke-RestMethod -Method Post `
  -Uri http://localhost:8080/realms/job-process/protocol/openid-connect/token `
  -Body @{ grant_type = 'password'; client_id = 'job-process-dev'; username = 'candidate@example.com'; password = 'DevPassword123!'; scope = 'openid email profile' }
).access_token
```

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/auth/me -Headers @{ Authorization = "Bearer $token" }
```

The first call creates the local `users` row, linked to Keycloak through `keycloak_sub`. Use the
same header for every other endpoint. Access tokens are valid for **15 minutes**; fetch a new one
when you get `401 Token has expired`.

**Swagger UI:** open <http://localhost:8000/docs>, click **Authorize**, and paste the value of
`$token`. Don't include the `Bearer ` prefix.

**Postman:** the collection creates its own Keycloak users through the Admin API. See
[postman/README.md](../postman/README.md). The environment's `keycloak_url` must be
`http://localhost:8080` (see the host name note above).

## 6. Front-end configuration (SPA)

Use any OIDC client library (for example `keycloak-js`, `angular-oauth2-oidc` or `oidc-client-ts`)
with:

| Setting | Value |
|---|---|
| Authority / issuer | `http://localhost:8080/realms/job-process` |
| Client ID | `job-process-web` |
| Flow | Authorization Code + PKCE (`S256`) |
| Scopes | `openid email profile` |
| Redirect URI | `http://localhost:4200/...` or `http://localhost:5173/...` |

Send the access token, not the ID token, as `Authorization: Bearer <token>` to the API.

## 7. Common tasks

**Add a user:** in the admin console, go to **job-process** realm → **Users** → **Add user**.
Set the email, turn on **Email verified**, then set a password under **Credentials** with
**Temporary** turned off. You can also self-register from the account URL above.

**Make a user an admin:** go to **Users** → *user* → **Role mapping** → **Assign role** and pick
`admin`. The API picks up the role on that user's next token.

**Link an existing (pre-Keycloak) app user:** create the Keycloak user with the **same email**
and turn on **Email verified**. On their first API call, the existing `users` row is linked and
keeps all its data.

**Reset Keycloak to the realm file:** Keycloak data lives inside the container, so recreating the
container starts again from `realm-export.json`. This removes any users or changes made in the
console.

```powershell
docker compose -f docker-compose.postman.yml up -d --force-recreate keycloak
```

**Change the realm permanently:** edit `keycloak/realm-export.json`, then recreate the container
as shown above. To copy changes you made in the console, use **Realm settings** → **Action** →
**Partial export** and merge the relevant parts into the file.

**Stop / remove:**

```powershell
docker compose -f docker-compose.postman.yml stop keycloak
```

```powershell
docker compose -f docker-compose.postman.yml rm -sf keycloak
```

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `401 Could not validate credentials` with a fresh token | Issuer mismatch (`localhost` vs `127.0.0.1`, or a different port). Decode the token at <https://jwt.io> *only for dev tokens* and compare `iss` with `KEYCLOAK_SERVER_URL`. Also check that `aud` contains `job-process-api`. |
| `401 Token has expired` | Fetch a new token (15-minute lifetime). |
| `503 Identity provider unavailable` | The API cannot reach the JWKS URL. Make sure Keycloak is running and healthy. If the API runs in Docker, set `KEYCLOAK_JWKS_URL=http://keycloak:8080/realms/job-process/protocol/openid-connect/certs`, and set `KEYCLOAK_ISSUER` to whatever host your tokens are issued from. |
| `403 Verify your email address…` | An existing app user has the same email but the Keycloak user isn't marked **Email verified**. |
| `409 Email is already linked to another account` | That email is already linked to a different Keycloak user (`keycloak_sub`). |
| `invalid_grant` / `Account is not fully set up` from the token endpoint | Wrong password, or the user has required actions pending (temporary password, verify email). Fix them in the user's **Details** / **Credentials** page. |
| `unauthorized_client` | You used `job-process-web` for a password grant. Use `job-process-dev` instead. |
| Container stays `starting`/`unhealthy` | `docker compose -f docker-compose.postman.yml logs keycloak`. Usually port 8080 is already in use; change the host port in `"127.0.0.1:8080:8080"` (for example `"127.0.0.1:8081:8080"`) and update `KEYCLOAK_SERVER_URL`. Right after recreating the container, a `ports are not available` error can be transient while the old container releases the port; run `up` again. |
| Keycloak not reachable from another device (phone, VM, colleague) | Expected: the port is bound to `127.0.0.1` only. For a temporary exception, change the mapping to `"8080:8080"` and don't commit it. |
| Realm changes not applied | The realm is imported at start-up only; recreate the container (see above). |
