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

for jobcontent variation use this

```powershell
 .\postman\multi-job-process.ps1
```

for single jobcontent variation use this

```powershell
 .\postman\single-job-process.ps1
```

and follow with

```powershell
newman run postman/Talent-Intelligence-Platform.postman_collection.json -e postman/Talent-Intelligence-Platform.local.postman_environment.json -d postings.json
```

some usefules variation
**Force a single URL source for the whole run**

```powershell
newman run collection.json -d postings.json --env-var "jobSource=indeed"
```

**Run only the first 5 postings**

```powershell
newman run collection.json -d postings.json -n 5
```

**Export results for CI**

```powershell
newman run collection.json -d postings.json -r cli,junit --reporter-junit-export results.xml
```

The collection includes successful and expected-failure checks for all requested operational,
authentication, profile, processing job, matching, and CV tailoring routes. The job-normalization
folder is a prerequisite that supplies a real job for successful matching tests. Matching requests
return `202 Accepted`; the collection polls the matching processing job before requesting report
results.
