Analyze this Odoo module completely and generate comprehensive documentation in its README.md file. The README must be bilingual: technical sections in English, functional sections in Spanish. Follow these exact instructions:

---

## ANALYSIS PHASE

Before writing anything, thoroughly read and analyze:

1. `__manifest__.py` — name, version, summary, description, depends, data files, author, license
2. All Python files in `models/` — every model (class), every field (name, type, string, help), every method with business logic
3. All Python files in `wizards/` (if any) — wizard models, their fields and logic
4. All XML files in `views/` — view names, menus, action names as displayed in Odoo UI
5. All XML files in `data/` and `security/` — default data, access groups, record rules
6. All XML files in `report/` (if any) — report names and triggers
7. All files in `controllers/` (if any) — exposed endpoints
8. `__init__.py` files to confirm which models/wizards are loaded

Do NOT generate the README until you have read ALL files listed above.

---

## README STRUCTURE

Generate the file `README.md` at the module root with EXACTLY this structure:

---
```markdown
# [Module Technical Name] — [Module Display Name from manifest]

> **Version:** [version from manifest] | **License:** [license] | **Author:** [author]

<!-- ============================================================ -->
<!-- ENGLISH SECTION — Technical Reference                        -->
<!-- ============================================================ -->

## Overview

[2–4 sentences describing what the module does technically. Include which Odoo native models it extends.]

## Dependencies

### Odoo / OCA Modules
[List every entry in `depends` from the manifest, one per line with a brief note on why it's needed]

### Python Libraries
[List any imports in Python files that are not part of Odoo standard. If none, write "None."]

## Installation

1. Place the module in your addons path.
2. Update the module list: **Settings → Activate Developer Mode → Update Apps List**
3. Search for `[module name]` and click **Install**.
4. [Add any post-install configuration step if detected in data/ files]

## Models Reference

[For each model found in models/, generate a subsection:]

### `[model._name]` — [model._description]

| Field Name | Type | Label (string) | Description |
|---|---|---|---|
| [field_name] | [field_type] | [string attr] | [help attr or inferred purpose] |

**Key methods:**
- `[method_name]`: [one-line technical description of what it does]

[Repeat for every model]

## Security Groups

[List groups defined in security/ir.model.access.csv or XML, with their access level per model]

## Menus & Actions

[List every menu item found in views/, with its full path as it appears in Odoo, e.g., "Inventory > Configuration > Custom Rules"]

## Reports

[List every QWeb report: name, model it applies to, trigger (button/action)]

## Controllers / API Endpoints

[If controllers/ exists, list each route, method (GET/POST), and purpose. If none, omit this section.]

---

<!-- ============================================================ -->
<!-- SECCIÓN EN ESPAÑOL — Documentación Funcional                 -->
<!-- ============================================================ -->

## Descripción General

[3–5 párrafos explicando en lenguaje de negocio qué problema resuelve este módulo, para qué área de la empresa está diseñado y cuál es su valor principal. Evitar tecnicismos. Redactar como si se lo explicaras a un gerente de área.]

## Objetivo de Negocio

[Lista de 3–6 bullets con los objetivos concretos que este módulo cumple dentro del proceso de negocio del cliente.]

## Flujos de Negocio Principales

[Para cada flujo de negocio identificado en el análisis del código, documenta:]

### Flujo [N]: [Nombre descriptivo del flujo]

**Descripción:** [Qué desencadena este flujo y qué resultado produce]

**Pasos:**
1. [Paso 1 — en términos de lo que hace el usuario en Odoo]
2. [Paso 2]
3. [...]

**Reglas de negocio importantes:**
- [Validaciones, restricciones o automatizaciones detectadas en el código]

[Repetir para cada flujo identificado]

## Guía de Configuración

[Lista ordenada de los pasos necesarios para configurar el módulo correctamente después de instalarlo. Incluir menús exactos de Odoo, valores recomendados y advertencias si el código tiene restricciones o dependencias de configuración.]

## Campos y Pantallas Clave

[Para cada modelo, describe en español los campos más importantes desde la perspectiva del usuario, usando el nombre que aparece en pantalla (string), no el nombre técnico:]

### [_description del modelo]

| Campo en pantalla | Para qué sirve | Valores posibles / Notas |
|---|---|---|
| [string] | [explicación funcional] | [si es selection, lista los valores; si tiene domain o constraint, explícalo en simple] |

## Automatizaciones y Reglas

[Si se detectaron automated actions, scheduled actions, o métodos que se disparan automáticamente, documéntalos aquí:]

- **[Nombre]:** Se ejecuta cuando [condición]. Resultado: [efecto en el sistema].

## Reportes Disponibles

[Si hay reportes, describe para qué sirve cada uno, cómo se accede y qué información muestra.]

## Preguntas Frecuentes (FAQ)

[Genera al menos 5 preguntas frecuentes que un usuario funcional podría hacer sobre este módulo, basándote en la lógica detectada en el código. Respóndelas en lenguaje simple.]

**P: [Pregunta]**
R: [Respuesta]

---

<!-- ============================================================ -->
<!-- NOTEBOOKLM TRAINING SECTION                                  -->
<!-- ============================================================ -->

## 🤖 Contexto para Asistente IA

> Esta sección está optimizada para el entrenamiento del asistente de IA del cliente.

**¿Qué hace este módulo en una oración?**
[Una oración clara y directa.]

**Palabras clave asociadas a este módulo:**
[Lista de 10–15 términos que un usuario podría usar al preguntar sobre este módulo: nombres de menús, nombres de campos en pantalla, conceptos de negocio relacionados, sinónimos comunes.]

**Casos de uso típicos:**
[5–8 ejemplos de preguntas o situaciones reales que este módulo resuelve, redactados como si vinieran del usuario final.]

**Lo que este módulo NO hace:**
[2–4 bullets sobre limitaciones o alcance, para evitar confusión en el bot.]
```

---

## WRITING RULES

- Never invent behavior not found in the code. If unsure, write "No determinado en el código."
- In the Spanish sections, always use the field's `string` attribute (UI label), never the Python field name.
- Menu paths must match exactly what appears in Odoo's UI based on the XML `name` attributes found in views.
- The FAQ section must have a minimum of 5 questions, maximum 10.
- The NotebookLM section must always be in Spanish.
- If the module has no reports, no controllers, or no wizards, omit those sections entirely without leaving empty headers.
- Do not truncate or summarize the Models Reference table — include every field of every model.
- Overwrite any existing README.md content completely.

## EXECUTION

After writing the README.md, print a brief summary in this format:
- Models documented: [N]
- Total fields documented: [N]
- Business flows identified: [N]
- FAQ questions generated: [N]
- Sections omitted (if any): [list]
