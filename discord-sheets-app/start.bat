@echo off
echo ============================================
echo   Epic Boss Notifier - Iniciando...
echo ============================================

REM Verifica se o .env existe
if not exist ".env" (
    echo.
    echo [ERRO] Arquivo .env nao encontrado!
    echo Copie o arquivo .env.example para .env e preencha as chaves.
    echo.
    pause
    exit /b 1
)

REM Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERRO] Python nao encontrado!
    echo Instale Python em: https://www.python.org/downloads/
    echo Marque a opcao "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)

REM Instala dependencias se necessario
if not exist "venv\" (
    echo Criando ambiente virtual...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Instalando dependencias...
pip install -r requirements.txt -q

echo.
echo Servidor rodando em: http://localhost:5000
echo Pressione Ctrl+C para parar.
echo.
python app.py
pause
