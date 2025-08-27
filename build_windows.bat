@echo off
echo ===================================
echo   Procura - Build para Windows
echo ===================================

echo.
echo Instalando dependencias...
pip install -r requiriments.txt
pip install pyinstaller

echo.
echo Limpando builds anteriores...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo.
echo Gerando executavel para Windows...
pyinstaller procura.spec --clean --noconfirm

echo.
echo Verificando se o executavel foi criado...
if exist "dist\Procura.exe" (
    echo.
    echo ✅ Build concluido com sucesso!
    echo Executavel criado: dist\Procura.exe
    echo.
    echo Para testar, execute: dist\Procura.exe
) else (
    echo.
    echo ❌ Erro durante o build!
    echo Verifique as mensagens de erro acima.
)

echo.
echo Pressione qualquer tecla para continuar...
pause > nul