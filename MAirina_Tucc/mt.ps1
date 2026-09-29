# MAirina Tucc: run `mt <command>` with the toolshop venv. Usage: .\mt.ps1 rhyme imas --lane drill
$py = "D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe"
$env:PYTHONPATH = "D:\Projects\Music-AI-Toolshop\MAirina_Tucc"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
& $py -W ignore -m mairina @args
exit $LASTEXITCODE
