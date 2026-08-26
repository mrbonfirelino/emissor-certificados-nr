# Gerador de Certificados NR - ALTEC

Sistema desktop para emissão de certificados de treinamento NR (Normas Regulamentadoras) com templates configuráveis, interface moderna e geração de PDF profissional.

## 📋 Funcionalidades

- **10 NRs pré-configuradas**: NR-01, NR-05, NR-06, NR-09, NR-10, NR-11, NR-12, NR-17, NR-18, NR-35
- **Templates em JSON**: Um arquivo por NR, fácil de editar e adicionar novos
- **Interface moderna**: CustomTkinter com tema azul corporativo
- **Cadastro de funcionários**: CRUD simples (Nome + CPF) com autocomplete no formulário
- **Configuração da empresa**: Dados fixos (CNPJ, Local, Instrutor, Registro MTE)
- **Numeração automática**: CERT-000001, CERT-000002...
- **PDF A4 Landscape**: Layout profissional com logo, conteúdo programático em 2 colunas, assinaturas
- **Histórico**: Busca, filtros, abertura de PDF/pasta
- **Backup automático**: Semanal silencioso + backup manual
- **Restauração com senha**: Proteção contra exclusão acidental
- **Executável standalone**: .exe único via PyInstaller

## 🚀 Instalação e Execução

### Pré-requisitos
- Python 3.10+
- Windows 10/11

### Modo Desenvolvimento
```bash
# 1. Clone/baixe o projeto
cd certificados-nr

# 2. Instale dependências
pip install -r requirements.txt

# 3. Prepare assets (ícone, fontes)
python setup_assets.py

# 4. Execute
python -m src.main
```

### Build Executável (.exe)
```bash
# Gera CertificadosNR.exe em dist/
python build/build_exe.py
```

### Distribuição
Copie a pasta `dist/` completa para a máquina alvo. O `.exe` é totalmente standalone.

## 📁 Estrutura do Projeto

```
certificados-nr/
├── src/
│   ├── main.py                 # Entry point
│   ├── core/                   # Lógica de negócio
│   │   ├── config.py           # Config empresa + senha restore
│   │   ├── models.py           # Pydantic models
│   │   ├── template_loader.py  # Carrega templates JSON
│   │   ├── pdf_generator.py    # Gera PDF (reportlab)
│   │   ├── certificate_service.py
│   │   ├── employee_repo.py    # CRUD funcionários
│   │   ├── history_repo.py     # Histórico + numeração
│   │   ├── backup_manager.py   # Backup auto/manual + restore
│   │   └── signature/          # Preparado para assinatura digital
│   ├── ui/                     # Interface CustomTkinter
│   │   ├── app.py              # Janela principal + navegação
│   │   ├── pages/              # Telas (Home, Funcionários, Histórico, Config, Backup)
│   │   ├── components/         # Componentes reutilizáveis
│   │   └── styles.py           # Tema azul corporativo
│   └── utils/                  # Utilitários
├── templates/                  # Um .template.json por NR
│   ├── _layout.json            # Layout visual compartilhado
│   ├── NR-01.template.json
│   ├── NR-05.template.json
│   ├── NR-06.template.json
│   ├── NR-09.template.json
│   ├── NR-10.template.json
│   ├── NR-11.template.json
│   ├── NR-12.template.json
│   ├── NR-17.template.json
│   ├── NR-18.template.json
│   └── NR-35.template.json
├── assets/
│   ├── LOGO TIPO ALTEC.png     # Logo da empresa
│   ├── logo.ico                # Ícone do .exe (gerado)
│   └── fonts/                  # DejaVu Sans (opcional)
├── data/                       # Criado em runtime
│   ├── certificados.db         # SQLite
│   └── backups/                # Backups .db.gz
├── build/                      # Scripts de build
├── requirements.txt
├── setup_assets.py
└── README.md
```

## ⚙️ Configuração Inicial

Na primeira execução, a tela de **Configuração** será exibida. Preencha:

| Campo | Exemplo |
|-------|---------|
| Nome da Empresa | ALTEC LTDA |
| CNPJ | 12.345.678/0001-90 |
| Local do Treinamento | ALTEC LTDA - UNIDADE INDUSTRIAL |
| Instrutor Responsável | João da Silva |
| Registro MTE | MTE 44633/RJ |
| Senha de Restauração | (opcional, mas recomendada) |

## 📝 Adicionando/Editando NRs

1. Copie um template existente em `templates/`
2. Renomeie para `NR-XX.template.json` (ex: `NR-20.template.json`)
3. Edite os campos:
   - `nr_code`: "NR-XX"
   - `nr_name`: Nome completo
   - `carga_horaria_minima`: Horas mínimas
   - `validade_anos`: Validade do certificado
   - `descricao_padrao`: Texto padrão do treinamento
   - `campos_extra`: Campos específicos do NR
   - `conteudo_programatico`: Lista de itens
   - `texto_certificado`: Template com placeholders `{campo}`
   - `assinaturas`: Blocos de assinatura

4. Reinicie o programa - o novo NR aparecerá automaticamente

### Placeholders disponíveis no `texto_certificado`:
- `{nome_funcionario}`, `{cpf}`, `{cargo}`, `{empresa}`, `{cnpj}`
- `{local_treinamento}`, `{instrutor_nome}`, `{instrutor_registro_mte}`
- `{data_inicio}`, `{data_fim}`, `{carga_horaria}`, `{descricao_treinamento}`
- Todos os `campos_extra` definidos no template

## 💾 Backup e Restauração

### Backup Automático
- Executado silenciosamente toda semana
- Mantém últimos 12 backups
- Armazenado em `data/backups/certificados_auto_YYYYMMDD_HHMMSS.db.gz`

### Backup Manual
- Botão "📥 Backup Manual Agora" na página Backup
- Nome: `certificados_manual_YYYYMMDD_HHMMSS.db.gz`

### Restauração
1. Página Backup → "🔄 Restaurar Backup"
2. Seleciona arquivo de backup
3. Digita senha de restauração
4. Confirmação dupla (apaga dados atuais!)

> **Importante**: A senha de restauração é definida na Configuração da Empresa. O hash Argon2 é salvo em `data/restore.key`.

## 🔮 Roadmap Futuro

- [ ] **Alertas de Vencimento**: Dashboard com certificados vencendo em 30/7/1 dias
- [ ] **Assinatura Digital ICP-Brasil**: Integração com SafeSign/GDOCS
- [ ] **Relatórios**: Exportar histórico para Excel/PDF
- [ ] **Múltiplas Empresas**: Suporte a filiais
- [ ] **Importação em Lote**: CSV de funcionários
- [ ] **Templates Visuais**: Editor drag-and-drop de layout

## 🛠️ Tecnologias

| Camada | Tecnologia |
|--------|------------|
| UI | CustomTkinter 5.2+ |
| PDF | ReportLab 4.2+ |
| Dados | Pydantic 2.8+ + SQLite |
| Backup | APScheduler + gzip |
| Segurança | Argon2 (hash senha restore) |
| Build | PyInstaller 6.8+ |

## 📄 Licença

Uso interno - ALTEC