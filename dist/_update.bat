@echo off
taskkill /F /IM Virtua.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul
start "" "C:\Users\DoubleTec Cliente\Desktop\a\Jarvis\versao_alunos\dist\Virtua.exe"
del "%~f0"
