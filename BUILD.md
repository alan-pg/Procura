# 📦 Guia de Build - Procura

Este guia explica como criar executáveis do projeto Procura para Windows e macOS.

## 📋 Pré-requisitos

### Para ambas as plataformas:
- Python 3.7 ou superior
- pip (gerenciador de pacotes Python)
- Conexão com a internet (para instalar dependências)

### Para Windows:
- Windows 7 ou superior
- PowerShell ou Command Prompt

### Para macOS:
- macOS 10.13 (High Sierra) or superior  
- Terminal
- Xcode Command Line Tools (instale com: `xcode-select --install`)

## 🚀 Como gerar os executáveis

### 🪟 Windows

1. **Abra o Command Prompt ou PowerShell como administrador**

2. **Navegue até a pasta do projeto:**
   ```cmd
   cd C:\caminho\para\Procura
   ```

3. **Execute o script de build:**
   ```cmd
   build_windows.bat
   ```

4. **Aguarde o processo finalizar.** O executável será criado em `dist/Procura.exe`

5. **Teste o executável:**
   ```cmd
   dist\Procura.exe
   ```

### 🍎 macOS

1. **Abra o Terminal**

2. **Navegue até a pasta do projeto:**
   ```bash
   cd /caminho/para/Procura
   ```

3. **Execute o script de build:**
   ```bash
   ./build_macos.sh
   ```

4. **Aguarde o processo finalizar.** O app será criado em `dist/Procura.app`

5. **Teste o aplicativo:**
   ```bash
   open dist/Procura.app
   ```

6. **Para instalar no sistema, copie para Applications:**
   ```bash
   cp -r dist/Procura.app /Applications/
   ```

## 🛠️ Build manual (avançado)

Se preferir fazer o build manualmente:

### 1. Instalar dependências:
```bash
pip install -r requiriments.txt
pip install pyinstaller
```

### 2. Limpar builds anteriores:
```bash
# Linux/macOS
rm -rf dist build

# Windows
rmdir /s /q dist build
```

### 3. Executar PyInstaller:
```bash
pyinstaller procura.spec --clean --noconfirm
```

## 📁 Estrutura dos arquivos gerados

```
dist/
├── Procura.exe          # Windows: executável
└── Procura.app/         # macOS: bundle do aplicativo
    └── Contents/
        ├── MacOS/
        ├── Resources/
        └── Info.plist
```

## 🔧 Customizações

### Alterar ícone:
1. Substitua o arquivo `favicon.ico` por seu ícone personalizado
2. Para macOS, converta para formato `.icns`
3. Regenere o executável

### Alterar informações do app:
Edite o arquivo `procura.spec`:
- `name`: Nome do executável
- `icon`: Caminho para o ícone
- `bundle_identifier`: ID único (macOS)
- `info_plist`: Informações do app (macOS)

## ❗ Solução de problemas

### Erro: "ModuleNotFoundError"
- Certifique-se que todas as dependências estão instaladas
- Adicione módulos faltantes no `hiddenimports` do arquivo `procura.spec`

### Executável muito grande:
- Use `--exclude-module` para remover módulos desnecessários
- Configure UPX para compressão (já habilitado)

### App não abre no macOS:
- Verifique permissões: `chmod +x dist/Procura.app/Contents/MacOS/Procura`  
- Desabilite Gatekeeper temporariamente: `sudo spctl --master-disable`

### Windows Defender bloqueia:
- Adicione exceção para a pasta `dist/`
- Assine digitalmente o executável (para distribuição)

## 📝 Notas importantes

- O build deve ser feito na plataforma de destino (Windows para .exe, macOS para .app)
- Executáveis podem ser grandes (~100-200MB) devido ao Python embarcado
- Primeiro execute sempre demora mais (PyInstaller analisa dependências)
- Para distribuição comercial, considere assinatura digital

## 🆘 Suporte

Em caso de problemas:
1. Verifique as mensagens de erro no terminal
2. Confirme que todas as dependências estão instaladas
3. Teste o script Python original antes do build
4. Consulte a documentação do PyInstaller: https://pyinstaller.org/