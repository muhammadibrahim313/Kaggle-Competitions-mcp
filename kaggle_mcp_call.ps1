param(
    [Parameter(Mandatory = $true)]
    [string]$ToolName,

    [string]$RequestJson = "{}",

    [string]$Token = "",

    [string]$TokenFile = "token"
)

$ErrorActionPreference = "Stop"

if (-not $Token) {
    if ($env:KAGGLE_TOKEN) {
        $Token = $env:KAGGLE_TOKEN
    } elseif ($env:kaggle_mcp_token) {
        $Token = $env:kaggle_mcp_token
    } elseif (Test-Path $TokenFile) {
        $Token = (Get-Content -Path $TokenFile -Raw).Trim()
    } elseif (Test-Path ".env") {
        $dotenv = Get-Content -Path ".env" -Raw -ErrorAction SilentlyContinue
        foreach ($line in $dotenv -split "[\r\n]+") {
            if ($line.Trim().StartsWith("#") -or -not $line.Contains("=")) { continue }
            $parts = $line.Split('=', 2)
            $k = $parts[0].Trim().ToLower()
            $v = $parts[1].Trim().Trim('"').Trim("'")
            if ($k -eq "kaggle_token" -or $k -eq "kaggle_mcp_token") {
                $Token = $v
                break
            }
        }
    }
}

if (-not $Token) {
    throw "No Kaggle token found. Set `$env:KAGGLE_TOKEN or `$env:kaggle_mcp_token, or create a token file."
}

$headers = @{
    Accept        = "application/json, text/event-stream"
    Authorization = "Bearer $Token"
}

$webSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession

$initBody = @{
    jsonrpc = "2.0"
    id      = 1
    method  = "initialize"
    params  = @{
        protocolVersion = "2025-03-26"
        capabilities    = @{}
        clientInfo      = @{
            name    = "PowerShell"
            version = "1.0"
        }
    }
} | ConvertTo-Json -Depth 10 -Compress

Invoke-WebRequest `
    -UseBasicParsing `
    -WebSession $webSession `
    -Method Post `
    -Uri "https://www.kaggle.com/mcp" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $initBody | Out-Null

$requestObject = if ([string]::IsNullOrWhiteSpace($RequestJson)) {
    @{}
} else {
    $RequestJson | ConvertFrom-Json
}

$callBody = @{
    jsonrpc = "2.0"
    id      = 2
    method  = "tools/call"
    params  = @{
        name      = $ToolName
        arguments = @{
            request = $requestObject
        }
    }
} | ConvertTo-Json -Depth 20 -Compress

$rawContent = (Invoke-WebRequest `
    -UseBasicParsing `
    -WebSession $webSession `
    -Method Post `
    -Uri "https://www.kaggle.com/mcp" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $callBody).Content

$jsonText = ($rawContent -split "`n" |
    Where-Object { $_ -like "data:*" } |
    ForEach-Object { $_.Substring(5).Trim() }) -join "`n"

$response = $jsonText | ConvertFrom-Json

if ($response.result.isError) {
    $response.result.content | ForEach-Object {
        if ($_.text) {
            Write-Output $_.text
        } else {
            $_ | ConvertTo-Json -Depth 20
        }
    }
    exit 1
}

if ($response.result.content) {
    foreach ($item in $response.result.content) {
        if ($item.type -eq "text" -and $item.text) {
            Write-Output $item.text
        } else {
            $item | ConvertTo-Json -Depth 20
        }
    }
} else {
    $response.result | ConvertTo-Json -Depth 20
}
