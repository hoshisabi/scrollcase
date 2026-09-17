#requires -Version 5.1
<#
.SYNOPSIS
  Thin wrapper — delegates to the global linker in ~/bin/link-skills.ps1.
#>
[CmdletBinding()]
param(
    [switch] $DryRun,
    [switch] $Prune
)

& "$env:USERPROFILE\bin\link-skills.ps1" `
    -RepoRoot (Split-Path -Parent $PSScriptRoot) `
    -DryRun:$DryRun `
    -Prune:$Prune
