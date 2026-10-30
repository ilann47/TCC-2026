param([string]$Repo = (Resolve-Path "$PSScriptRoot\..\..\..").Path,
      [Parameter(Mandatory=$true)][string]$Build)
$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path -LiteralPath $Repo).Path
$buildPath = [IO.Path]::GetFullPath($Build)
if (Test-Path -LiteralPath $buildPath) { throw 'Use uma pasta nova para cada compilacao.' }
$sourcePath = Join-Path $buildPath 'src'
New-Item -ItemType Directory -Path $sourcePath -Force | Out-Null
$original = Join-Path $repoPath 'projeto-latex-java'
# Copia somente fontes e imagens; nunca reutiliza aux/toc/bbl de outra versao.
Get-ChildItem -LiteralPath $original -File -Recurse | Where-Object {
    $_.Extension -in '.tex','.cls','.sty','.bst','.bib','.def','.cfg','.clo','.png','.jpg','.jpeg','.puml','.svg','.eps' -and
    $_.FullName -notmatch '[\\/]qa-render[\\/]'
} | ForEach-Object {
    $relativePath = [IO.Path]::GetRelativePath($original,$_.FullName)
    $destination = Join-Path $sourcePath $relativePath
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $destination
}
$latex = (Get-Command pdflatex -ErrorAction Stop).Source
$bibtex = (Get-Command bibtex -ErrorAction Stop).Source
Push-Location $sourcePath
try {
    $texArguments = @('-disable-installer','-interaction=nonstopmode','-halt-on-error','modelo.tex')
    & $latex @texArguments *> (Join-Path $buildPath 'latex-1.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Falha na primeira passagem LaTeX; consulte latex-1.txt.' }
    & $bibtex 'modelo' *> (Join-Path $buildPath 'bibtex.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Falha no BibTeX; consulte bibtex.txt.' }
    foreach ($pass in 2..4) {
        & $latex @texArguments *> (Join-Path $buildPath "latex-$pass.txt")
        if ($LASTEXITCODE -ne 0) { throw "Falha na passagem LaTeX $pass." }
    }
    $log = Get-Content 'modelo.log' -Raw
    if ($log -match 'undefined references|Citation .* undefined|Reference .* undefined|Overfull \\hbox|Overfull \\vbox|destination with the same identifier') {
        throw 'PDF compilado, mas o log exige revisao antes de publicar.'
    }
    Get-Item 'modelo.pdf' | Select-Object FullName,Length
} finally { Pop-Location }
