# Instalador — Inno Setup (planejamento)

> **Status: documento/planejamento.** Nenhum instalador foi gerado ainda.
> Quando decidir distribuir via instalador, copie o script abaixo para
> `installer/NormaTech.iss` e compile com o Inno Setup 6.

---

## Objetivo

Substituir a distribuição "extraia o zip" por um instalador `NormaTech_Setup_vX.Y.Z.exe`
que: cria atalho, ícone no menu Iniciar, verifica PowerPoint (requisito dos
cartões PPTX) e preserva os dados do usuário na desinstalação.

## Pré-requisitos

- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (compilar: `ISCC.exe`)
- Build `onedir` atual em `dist\CertificadosNR\` (ver `docs/BUILD.md`)
- `assets\logo.ico` (já existe)

## Script completo (`installer/NormaTech.iss`)

```ini
; NormaTech — Instalador (Inno Setup 6)
#define MyAppName "NormaTech"
#define MyAppVersion "1.4.0"
#define MyAppExeName "CertificadosNR.exe"
#define MyAppIcon "..\assets\logo.ico"

[Setup]
AppId={{8C1F2A90-6E4B-4C7D-9A2F-NORMATECH0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
SetupIconFile={#MyAppIcon}
OutputBaseFilename=NormaTech_Setup_v{#MyAppVersion}
OutputDir=Output
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest          ; instala em %LOCALAPPDATA% se sem admin
; ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Atalho na &área de trabalho"; GroupDescription: "Atalhos:"
Name: "runafter"; Description: "Executar o NormaTech ao concluir"; Flags: unchecked

[Files]
; pasta inteira do build onedir (exe + _internal + templates + data iniciais)
Source: "..\dist\CertificadosNR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Executar {#MyAppName}"; Flags: nowait postinstall skipifsilent; Tasks: runafter

[UninstallDelete]
; NUNCA apagar dados do usuário — remoção de dados é manual e consciente:
; data\ (banco+backups), CERTIFICADOS\ e as pastas externas permanecem.

[Code]
function PowerPointInstalado(): Boolean;
var
  reg: String;
begin
  Result := RegQueryStringValue(HKEY_CLASSES_ROOT,
    'PowerPoint.Application\CurVer', '', reg);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not PowerPointInstalado() then
    MsgBox('Microsoft PowerPoint nao foi detectado.' + #13#10 +
           'Os certificados funcionam normalmente, mas os CARTOES DE BLOQUEIO ' +
           'em modelo PPTX exigem o PowerPoint (Office).', mbInformation, MB_OK);
end;
```

## Como gerar

```powershell
# 1. build do app
python build/build_exe.py
# 2. compilar o instalador (ajuste o caminho do ISCC se preciso)
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\NormaTech.iss
# saida: installer\Output\NormaTech_Setup_v1.4.0.exe
```

## Decisões embutidas no script (ajustáveis)

| Decisão | Valor | Motivo |
|---------|-------|--------|
| `PrivilegesRequired=lowest` | Instala sem admin (fallback `%LOCALAPPDATA%`) | máquinas corporativas sem admin; `C:\NormaTech-Backup` só é criada se permitido (o app tolera) |
| Desinstalação preserva dados | `data\`, `CERTIFICADOS\`, pastas externas | desinstalar ≠ perder o banco |
| Verificação de PowerPoint | aviso, não bloqueia | certificados funcionam sem Office |
| Versão no script | manual (`#define`) | alinhar com CHANGELOG a cada release |

## Futuro (fora do escopo atual)

- Assinatura digital do instalador (certificado de código) — remove SmartScreen
- Atualização automática in-app (checar versão no GitHub e baixar novo setup)
- Instalação por máquina (`admin`) com dados em `C:\ProgramData\NormaTech`
