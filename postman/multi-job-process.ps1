
$items = Get-ChildItem ".\postman\fixtures\jobs\*.txt" -File |
ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName)

    [pscustomobject]@{
        content = $content
    }
}

$json = ConvertTo-Json -InputObject @($items) -Depth 3
Set-Content -Path "postings.json" -Value $json -Encoding utf8
