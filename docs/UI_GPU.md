# Interface com Aceleração GPU — Estudo (futuro)

Contexto: máquinas dos usuários têm **CPU fraca + GPU integrada**. A interface
atual (CustomTkinter/Tkinter) é renderizada por software (CPU/GDI) — sem GPU.
Este documento compara as opções para o cenário e lista quick-wins na stack
atual. **Nenhuma mudança de código foi feita com base neste estudo.**

---

## Antes de migrar: medir

1. Abrir o Gerenciador de Tarefas → aba Desempenho durante o uso pesado
   (emissão em massa, rolagem de listas grandes)
2. Se a CPU do app ficar < 30% num core e a interface ainda "arrastar",
   o gargalo pode ser outro (disco/OneDrive, GIL em threads, rebuild de listas)
3. Migrar UI só vale se a renderização for realmente o gargalo — a lógica
   (PDF, PPTX/COM, SQLite) continua igual em qualquer framework

## Comparativo (CPU fraca + GPU integrada, Windows)

| Opção | GPU? | RAM típica | Esforço de migração | Observações |
|-------|------|-----------|--------------------|-------------|
| **Manter Tkinter + quick-wins** | Não | ~80 MB | — | Ver seção abaixo; provavelmente suficiente |
| **PySide6 + Qt Quick (QML)** | Sim (scene graph, Direct3D11/OpenGL) | ~150 MB | Alto: UI inteira reescrita em QML | Widgets Qt clássicos também são CPU; só o QML usa GPU |
| **Flet (Flutter)** | Sim (Skia/Impeller) | ~250-350 MB | Médio: UI reescrita, lógica Python aproveitada | Melhor custo/benefício se migrar; apps fluidos em máquinas fracas; executável maior |
| **Dear PyGui** | Sim (DirectX 11/OpenGL) | ~100 MB | Médio-alto: paradigma immediate mode | Muito rápido; visual menos "corporativo desktop" |
| **Electron** | Sim (composição Chromium) | 300+ MB | Alto + frontend JS | RAM pesada — inadequado para máquinas fracas |
| **Tauri** | Sim (WebView2 do sistema) | ~120 MB | Alto + frontend JS | Leve (usa WebView2 do Windows); requer front-end web |

## Recomendação

1. **Curto prazo**: aplicar os quick-wins (abaixo) e medir de novo — a busca
   por Enter/botão (v1.3.2) já eliminou o maior pico de CPU por tecla.
2. **Se migrar um dia**: **Flet** (melhor equilíbrio GPU/RAM/esforço para um
   app de formulários + listas como este) ou **PySide6+QML** (equipe com
   conhecimento Qt). Evitar Electron.
3. Migração por etapas: manter o núcleo Python (src/core, templates, PPTX/COM)
   intacto e trocar apenas a camada `src/ui`.

## Quick-wins na stack atual (sem migração)

- Busca somente no Enter/botão (feito na v1.3.2 — zero re-render por tecla)
- Paginar listas grandes (já feito: funcionários/histórico/cartões/funções)
- Evitar recriar a página inteira ao navegar (já feito: cache de páginas no app)
- Manter fotos como miniaturas em cache (CTkImage já reutilizado nas linhas)
- Não usar animações/tema escuro dinâmico (não usados)
- Se necessário: reduzir `font_scale` global nas máquinas mais fracas
