# Postman Integration Tests

Import `Talent-Intelligence-Platform.postman_collection.json` and
`Talent-Intelligence-Platform.local.postman_environment.json`, then run the collection in order
against a running local API. The collection generates a unique user email and propagates its token
and resource identifiers automatically.

The `profile_fixture_path` environment variable must resolve to
`postman/fixtures/profile.txt` from the Postman or Newman working directory. Set it to an absolute
path when your client cannot resolve relative upload paths.

Run it from the repository root with Newman:

```powershell
newman run postman/Talent-Intelligence-Platform.postman_collection.json -e postman/Talent-Intelligence-Platform.local.postman_environment.json
```

The collection includes successful and expected-failure checks for all requested operational,
authentication, profile, processing job, matching, and CV tailoring routes. The job-normalization
folder is a prerequisite that supplies a real job for successful matching tests.
