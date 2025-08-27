#!/bin/bash

echo "==================================="
echo "   Procura - Build para macOS"
echo "==================================="

echo ""
echo "Instalando dependências..."
pip3 install -r requiriments.txt
pip3 install pyinstaller

echo ""
echo "Limpando builds anteriores..."
rm -rf dist build

echo ""
echo "Gerando aplicativo para macOS..."
pyinstaller procura.spec --clean --noconfirm

echo ""
echo "Verificando se o app foi criado..."
if [ -d "dist/Procura.app" ]; then
    echo ""
    echo "✅ Build concluído com sucesso!"
    echo "Aplicativo criado: dist/Procura.app"
    echo ""
    echo "Para testar, execute: open dist/Procura.app"
    echo "Ou arraste o Procura.app para a pasta Applications"
else
    echo ""
    echo "❌ Erro durante o build!"
    echo "Verifique as mensagens de erro acima."
fi

echo ""
echo "Pressione Enter para continuar..."
read