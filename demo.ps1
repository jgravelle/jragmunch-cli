# jragmunch-cli demo script
# Run with: .\demo.ps1
# Pauses between beats so you can capture clean cuts.

function Beat($label) {
    Write-Host ""
    Read-Host "[paused — press Enter for: $label]" | Out-Null
    Write-Host ""
}

Clear-Host

# ---- Beat 1: install ----
Write-Host "PS> pip install jragmunch" -ForegroundColor Cyan
Beat "doctor"
pip install --quiet jragmunch
Write-Host "Successfully installed jragmunch-0.4.0" -ForegroundColor DarkGray

# ---- Beat 2: verify ----
Write-Host ""
Write-Host "PS> jragmunch doctor" -ForegroundColor Cyan
Beat "the question"
jragmunch doctor

# ---- Beat 3: setup ----
Write-Host ""
Write-Host "# Ask a hard question about jcodemunch-mcp (a real 1,500-star repo)." -ForegroundColor DarkGray
Write-Host "# No file dumped into the prompt — only the slices the model retrieves." -ForegroundColor DarkGray
Beat "ask"

# ---- Beat 4: the money shot ----
$q = "How does the secret-redaction layer work, and which response fields does it touch?"
Write-Host "PS> jragmunch ask `"$q`" --repo C:\MCPs\jcodemunch-mcp" -ForegroundColor Cyan
Write-Host ""
jragmunch ask $q --repo C:\MCPs\jcodemunch-mcp

# ---- Beat 5: the pin ----
Beat "outro"
Write-Host ""
Write-Host "# Real answer. Real citations. Real `$0." -ForegroundColor Green
Write-Host "# Slice-level RAG for headless Claude." -ForegroundColor Green
Write-Host "# github.com/jgravelle/jragmunch-cli" -ForegroundColor Green
Write-Host ""
