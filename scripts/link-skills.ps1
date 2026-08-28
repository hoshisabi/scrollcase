<#
.SYNOPSIS
  Link the repo's skills into each agent tool's user-scope skills root.

.DESCRIPTION
  scrollcase keeps its skills in the repo at .claude/skills/<name>/SKILL.md so they
  stay in git. Agent tools only read their own user-scope directory, so each skill
  needs a junction pointing back here.

  For Claude specifically this is also a workaround for pingdotgg/t3code#6449: the
  T3 Code skill picker resolves "project scope" against the server process's startup
  directory (the home dir), never the open workspace, so a repo-local .claude/skills
  is unreachable. User scope is the only root it actually reads.

  Junctions, not copies: edit the file in the repo and every tool sees the change.
  Re-run after adding a skill, or after installing a new tool.

.PARAMETER DryRun
  Report what would change without touching the filesystem.

.PARAMETER Prune
  Also remove scrollcase junctions whose source directory is gone.
#>
[CmdletBinding()]
param(
    [switch] $DryRun,
    [switch] $Prune
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot  = Split-Path -Parent $PSScriptRoot
$sourceDir = Join-Path $repoRoot '.claude\skills'
$home_     = [Environment]::GetFolderPath('UserProfile')

if (-not (Test-Path $sourceDir)) {
    throw "No skills directory at $sourceDir"
}

# Each tool's user-scope skills root, and the directory whose presence means the
# tool is installed. Roots are only created when that marker already exists, so a
# tool you do not use never gets a stray directory.
#
# 'Verified' marks roots confirmed working on this machine. The rest follow the
# layouts reported in pingdotgg/t3code#2736 and are best-effort until tested.
#
# Note: Cursor's ~/.cursor/skills-cursor is Cursor-managed and sync-clobbered.
# User skills go in ~/.cursor/skills instead.
$targets = @(
    @{ Tool = 'Claude Code'; Root = "$home_\.claude\skills";          Marker = "$home_\.claude";          Verified = $true  }
    @{ Tool = 'Cursor';      Root = "$home_\.cursor\skills";          Marker = "$home_\.cursor";          Verified = $false }
    @{ Tool = 'Codex';       Root = "$home_\.codex\skills";           Marker = "$home_\.codex";           Verified = $false }
    @{ Tool = 'OpenCode';    Root = "$home_\.config\opencode\skill";  Marker = "$home_\.config\opencode"; Verified = $false }
    @{ Tool = 'OpenCode alt';Root = "$home_\.opencode\skill";         Marker = "$home_\.opencode";        Verified = $false }
    @{ Tool = 'Agent Skills';Root = "$home_\.agents\skills";          Marker = "$home_\.agents";          Verified = $false }
)

$skills = @(Get-ChildItem $sourceDir -Directory |
            Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') })

if ($skills.Count -eq 0) { throw "No <name>/SKILL.md directories under $sourceDir" }

Write-Host ""
Write-Host "Source: $sourceDir  ($($skills.Count) skills)" -ForegroundColor Cyan
if ($DryRun) { Write-Host "DRY RUN - nothing will be written" -ForegroundColor Yellow }
Write-Host ""

foreach ($t in $targets) {
    $tag = if ($t.Verified) { '' } else { ' (unverified layout)' }

    if (-not (Test-Path $t.Marker)) {
        Write-Host ("{0,-14} skipped - not installed ({1})" -f $t.Tool, $t.Marker) -ForegroundColor DarkGray
        continue
    }

    Write-Host ("{0,-14} {1}{2}" -f $t.Tool, $t.Root, $tag) -ForegroundColor White

    if (-not (Test-Path $t.Root)) {
        if ($DryRun) { Write-Host "    would create root" -ForegroundColor Yellow }
        else { New-Item -ItemType Directory -Path $t.Root -Force | Out-Null }
    }

    foreach ($s in $skills) {
        $link = Join-Path $t.Root $s.Name
        if (Test-Path $link) {
            $item = Get-Item $link -Force
            if ($item.LinkType -ne 'Junction') {
                # A real directory here is someone's actual work, not ours to delete.
                Write-Host "    !! $($s.Name) - real directory, leaving alone" -ForegroundColor Red
                continue
            }
            if ($item.Target -contains $s.FullName) { continue }   # already correct
            if ($DryRun) { Write-Host "    would repoint $($s.Name)" -ForegroundColor Yellow; continue }
            Remove-Item $link -Force
        }
        elseif ($DryRun) { Write-Host "    would link $($s.Name)" -ForegroundColor Yellow; continue }

        New-Item -ItemType Junction -Path $link -Target $s.FullName | Out-Null
        Write-Host "    linked $($s.Name)" -ForegroundColor Green
    }

    if ($Prune) {
        $names = $skills.Name
        Get-ChildItem $t.Root -Directory -Force |
            Where-Object { $_.LinkType -eq 'Junction' -and
                           $_.Target -and ($_.Target -join ';') -like "*$sourceDir*" -and
                           $names -notcontains $_.Name } |
            ForEach-Object {
                if ($DryRun) { Write-Host "    would prune $($_.Name)" -ForegroundColor Yellow }
                else { Remove-Item $_.FullName -Force; Write-Host "    pruned $($_.Name)" -ForegroundColor Magenta }
            }
    }
}

Write-Host ""
Write-Host "Done. Restart T3 Code to refresh its provider cache." -ForegroundColor Cyan
Write-Host ""
