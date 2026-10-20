# Agenda a geração/simulação; não ativa publicações e não guarda credenciais.
$ErrorActionPreference = 'Stop'
$ProjectFolder = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PythonPath = (Get-Command python -ErrorAction Stop).Source
$RoutinePath = Join-Path $PSScriptRoot 'rotina_diaria.py'
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument ('"' + $RoutinePath + '"') -WorkingDirectory $ProjectFolder
$Morning = New-ScheduledTaskTrigger -Daily -At '09:15'
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'PetNova-Conteudos-Demo' -Action $Action -Trigger $Morning -Settings $Settings -Description 'Gera conteúdos PetNova em simulação. Não publica nem cobra.' -Force
Write-Output 'Rotina registada às 09:15 na hora local deste Windows. O PC precisa de estar ligado.'
