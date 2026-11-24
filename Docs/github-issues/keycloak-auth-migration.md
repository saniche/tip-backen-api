# Migrate authentication from the app database to Keycloak

**Labels:** `enhancement`, `security`, `auth`, `breaking-change`

## Background

Today the API runs its own authentication:

- `POST /api/v1/auth/register` and `POST /api/v1/auth/login` check emails and passwords
  against `users.hashed_password`.
- `auth/security.py` creates HS256 JWTs signed with one shared `JWT_SECRET_KEY`.

This means the API owns password storage, has no MFA, password reset or social login, and
can't offer SSO across clients. We want **Keycloak** to be the identity provider. The API
becomes an OAuth2 resource server that only checks the access tokens Keycloak issues.

The app database still keeps a local **user record**. Every domain table (profiles, jobs,
matchings, applications, CVs…) has a foreign key to `users.id`, and the app needs local user
data for ownership checks and display.

## Scope

### 1. Keycloak setup
- [ ] Add a `keycloak` service to `docker-compose.postman.yml` that starts with `--import-realm`.
- [ ] Add `keycloak/realm-export.json` with:
  - [ ] the `job-process` realm
  - [ ] the `job-process-web` client: public, Authorization Code + PKCE, for the SPA
  - [ ] the `job-process-dev` client: public, direct-access grants enabled, for local and Postman use only
  - [ ] an audience mapper that adds `job-process-api` to the `aud` claim of access tokens
  - [ ] the realm roles `user` (default) and `admin`
  - [ ] a dev test user and a dev admin user
- [ ] Add the new environment variables: `KEYCLOAK_SERVER_URL`, `KEYCLOAK_REALM`,
      `KEYCLOAK_AUDIENCE`, `KEYCLOAK_ISSUER` (optional override), `KEYCLOAK_JWKS_URL` (optional
      override), `KEYCLOAK_ADMIN_ROLE`, `KEYCLOAK_JWKS_CACHE_SECONDS`.
- [ ] Remove `JWT_SECRET_KEY`.

### 2. App-database user table (`users`)
Reshape the existing table rather than replacing it, so that `users.id` and all foreign keys stay as they are.

| Column           | Type        | Notes                                                        |
|------------------|-------------|--------------------------------------------------------------|
| `id`             | string (PK) | Unchanged; the internal id that all foreign keys point to    |
| `keycloak_sub`   | string      | **New.** Unique, indexed; Keycloak `sub` claim. Nullable for legacy rows until they are linked |
| `email`          | string      | Unchanged, unique; synced from the token                     |
| `email_verified` | bool        | **New.** Synced from the token                               |
| `username`       | string      | **New.** `preferred_username`                                |
| `first_name`     | string      | **New.** `given_name`                                        |
| `last_name`      | string      | **New.** `family_name`                                       |
| `role`           | string      | Unchanged (`user`/`admin`); mapped from Keycloak roles on each request |
| `is_active`      | bool        | **New.** Default `true`; the app can block a user locally    |
| `created_at`     | timestamptz | Unchanged                                                    |
| `updated_at`     | timestamptz | **New**                                                      |
| `last_login_at`  | timestamptz | **New.** Updated when a token is seen                        |
| ~~`hashed_password`~~ | —      | **Dropped.** Passwords live only in Keycloak                 |

- [ ] Alembic migration `015_keycloak_users` (upgrade and downgrade).

### 3. Token validation
- [ ] Rewrite `auth/security.py` to check RS256 tokens against the realm JWKS. Cache the
      keys, and fetch them again when a token has an unknown `kid` (key rotation).
- [ ] Check the signature, `exp`, `iss` (the realm issuer) and `aud` (contains `KEYCLOAK_AUDIENCE`).
- [ ] Create or update the local user on each authenticated request (`auth/user_sync.py`):
  1. Look up the user by `keycloak_sub`.
  2. Otherwise, look up a legacy row by email, only when `email_verified` is true, and link it
     by setting `keycloak_sub`.
  3. Otherwise, create a new row.
- [ ] Map the admin role: `admin` in `realm_access.roles` or in
      `resource_access[<audience>].roles` gives `role = "admin"`.
- [ ] Return 401 for invalid or expired tokens and 403 for users that are deactivated locally.
- [ ] Keep the `get_current_user` and `user_is_admin` signatures, so domain routers don't change.

### 4. API surface (**breaking change**)
- [ ] Remove `POST /api/v1/auth/register` and `POST /api/v1/auth/login`. Clients
      sign in and register through Keycloak (OIDC).
- [ ] Add `GET /api/v1/auth/me`, which returns the local user record.
- [ ] Regenerate `openapi.json`.

### 5. Tests, docs and tooling
- [ ] In tests, sign tokens with an in-memory RSA key and stub the JWKS. Replace every
      `/auth/register` call with a token helper.
- [ ] Add unit tests: valid, expired, wrong issuer, wrong audience, bad signature,
      unknown `kid` refresh, legacy email linking, admin role mapping, inactive user, `/auth/me`.
- [ ] Update the README, `Docs/api-documentation.md`, the Postman collection (get the token
      from the Keycloak token endpoint) and the CI env.

## Acceptance criteria
- [ ] No passwords are stored or checked by the API, and `passlib` and `JWT_SECRET_KEY` are gone.
- [ ] A Keycloak access token for the `job-process` realm can call every protected endpoint.
- [ ] The first request with a new Keycloak user creates a `users` row with `keycloak_sub` set.
- [ ] An existing local user who signs in to Keycloak with the same verified email keeps all their data.
- [ ] Keycloak users with the `admin` role get admin behaviour (`require_owner_or_admin`, job write access).
- [ ] Tokens that are expired, from another issuer or audience, or tampered with get `401` with the shared error envelope.
- [ ] `alembic upgrade head` and `alembic downgrade -1` both succeed.
- [ ] The full `pytest` suite passes in CI.

## Migrating existing users
1. Create the accounts in Keycloak with the same emails, either by import or by asking users to
   self-register, and mark the emails as verified.
2. On a user's first Keycloak login, their legacy row is linked by email automatically.
3. Passwords are **not** migrated. Users set a new password in Keycloak, for example with a
   "reset password" email.

## Out of scope
- Frontend OIDC integration (tracked separately).
- Syncing users from Keycloak to the app through admin events or webhooks. Users are created on demand when they first call the API.
- Fine-grained authorization beyond `user`/`admin`.
