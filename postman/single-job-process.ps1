
$selectedJob = Get-Content (
    Get-ChildItem ".\postman\fixtures\jobs\job-*.txt" -File |
    Where-Object { $_.BaseName -match '^job-0[0-6]$' } |
    Get-Random
).FullName -Raw

$items = @(
    [pscustomobject]@{
        content = [string]$selectedJob
    }
)

ConvertTo-Json -InputObject $items |
    Set-Content -Path "postings.json" -Encoding utf8
