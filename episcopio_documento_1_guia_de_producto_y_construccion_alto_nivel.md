# Episcopio — Guía de Producto y Construcción (Documento 1)

> **Propósito de este documento**: servir como **instrucciones de alto nivel** para que un asistente de inteligencia artificial (IA Builder) construya **Episcopio**, una plataforma de monitoreo epidemiológico para México. Aquí se define el *qué* y el *por qué* (alcance, usuarios, funcionalidades, flujos, datos, KPIs, riesgos, roadmap y playbook operativo). El **Documento 2** contendrá la especificación técnica detallada (APIs, esquemas, pipelines, repos, IaC).

---

## 1) Visión y contexto

**Nombre del proyecto:** *Episcopio*  
**Eslogan sugerido:** *“Tomando el pulso epidemiológico de México”*  
**Idea central:** integrar **datos oficiales** (DGE/SINAVE, INEGI, anuarios y boletines) con **señales complementarias** (sondeos voluntarios de clínicos y monitoreo público de redes) para ofrecer **visualizaciones prácticas**, **alertas tempranas** y **boletines ejecutivos** de utilidad clínica y de salud pública.

**Dolores actuales** (que Episcopio resuelve):
- Retrasos y baja “digeribilidad” de información oficial.
- Falta de síntesis visual/interpretativa para tomas de decisión rápidas.
- Señales locales que tardan en aparecer en canales formales.

**Principios de diseño**: simplicidad, rapidez de acceso, enfoque clínico, transparencia metodológica, ética y privacidad.

---

## 2) Objetivos

### 2.1 Objetivo general
Construir un **dashboard web/app** que brinde **actualizaciones periódicas** con datos oficiales y **un módulo de sondeo clínico/social** para un panorama **práctico y sintético** destinado a profesionales de la salud.

### 2.2 Objetivos específicos
1) Ingerir, limpiar y mostrar **series oficiales** (por entidad/municipio, por morbilidad).  
2) **Sondeo clínico**: formulario anónimo para reportes breves (síntomas atípicos, picos locales).  
3) **Monitoreo público** de redes (palabras clave/hashtags de salud) como señal temprana.  
4) **Boletín** semanal/quincenal con hallazgos y contexto.  
5) Mantener **UX clara y rápida**.

---

## 3) Usuarios objetivo y casos de uso

- **Médicos de primer contacto/GPs**: panorama local para sospecha diagnóstica, preparación de insumos, comunicación con pacientes.  
- **Epidemiólogos estatales/municipales**: vigilancia situacional, cruces con factores demográficos.  
- **Salud pública/gestores**: seguimiento de tendencias y priorización de acciones.  
- **Comunidad académica/ONGs**: insumos para investigación y vigilancia participativa.

**Casos de uso típicos**
- Consultar **curva temporal** y **mapa** por entidad/diagnóstico.  
- Revisar **comparativo** oficial vs. red social + **sentimiento**.  
- Recibir **alertas** (picos súbitos, cambios de tendencia, señales sociales).  
- Descargar **CSV/Excel** para análisis propio.  
- Enviar **reporte clínico breve** (opcional, anónimo).

---

## 4) Alcance funcional (MVP → V1)

### 4.1 MVP (versión mínima)
1. **Panel oficial**: KPIs (casos confirmados, activos, defunciones), serie temporal y mapa por entidad.  
2. **Panel social/sondeo**: nivel agregado de menciones (por keyword/hashtag), sentimiento básico; formulario de sondeo.  
3. **Alertas**: reglas simples (p. ej., ↑10–20% 3 días vs. media 14 días; picos de menciones; viraje a sentimiento negativo).  
4. **Boletín**: plantilla automática semanal/quincenal (resumen + highlights + recomendaciones).  
5. **Histórico/archivo**: consulta por fechas, exportaciones.

### 4.2 V1 (posterior al MVP)
- **Filtros avanzados** (municipio, grupo etario, sexo si disponible).  
- **Anomalías** (z-score, STL, CUSUM) y **correlación** oficial–social a ventana móvil.  
- **Perfiles de usuario/roles** (admin, clínico, observador).  
- **Panel de calidad de datos** (completitud, latencia, tasa de errores).  
- **Entregables**: API pública de lectura, exportación de reportes en PDF/HTML, *webhooks* de alertas.

---

## 5) Fuentes de datos (catálogo)

### 5.1 Oficiales (prioridad alta)
- **DGE/SINAVE/SUAVE**: morbilidades de notificación; boletines epidemiológicos y anuarios.  
- **Datos abiertos SSA/CONACYT (COVID-19, históricos)**.  
- **INEGI**: indicadores demográficos/socioeconómicos para denominadores y contexto.  
- **Portales estatales**: boletines y tableros locales.

### 5.2 Complementarias
- **Redes sociales públicas**: X/Twitter (geocontenidos, palabras clave), Facebook/Instagram (público), noticias/sitios de salud (web scraping ligero con respeto a términos).  
- **Sondeo clínico**: formulario web con anonimato total.

> *Nota*: toda recolección cumple Términos & Condiciones, robots.txt y **privacidad por diseño**.

---

## 6) Métricas, KPIs y OKRs

**KPIs del panel** (por periodo/ámbito):
- **Casos confirmados**, **activos**, **defunciones**.  
- **Menciones sociales** relevantes y **sentimiento** agregado.  
- **Alertas activas** (tipo, fecha, umbral que gatilló).  

**KPIs de producto/operación**:
- Latencia de datos (ingesta→dashboard).  
- Tasa de éxito de pipelines y scraping; tiempo hasta emisión de **boletín**.  
- Participación en sondeo (n. entradas/semana) y cobertura geográfica.

**OKRs (ejemplo de trimestre)**
- **O1**: Validar utilidad clínica del MVP con ≥20 usuarios.  
  - KR1: ≥2 insights accionables reportados/mes.
  - KR2: ≥90% de uptime del dashboard.  
- **O2**: Robustecer señales sociales.  
  - KR1: F1-score ≥0.75 en clasificación de relevancia.  
  - KR2: ↑ Cobertura geográfica a ≥24 entidades.

---

## 7) Experiencia de usuario (UX)

- **Home** con 4 tarjetas KPI (casos totales, activos, defunciones, alerta social).  
- **Controles**: selector de entidad, diagnóstico/morbilidad, rango de fechas.  
- **Vistas**: Serie temporal (oficial vs social), mapa coroplético, gráfico de sentimiento; feed de **alertas**.  
- **Acciones**: exportar CSV/Excel; abrir boletín; enviar reporte anónimo.  
- **Accesibilidad**: responsive, carga <2–3 s en vista principal.

**Estilo visual sugerido**: paleta sobria (azules/verde-azulado, grises; acentos ámbar para alertas), tipografía sans moderna (p. ej., Roboto, Open Sans, Lato). Iconografía clara para estados/alertas.

---

## 8) Gobernanza, privacidad y ética

- **Anonimato** absoluto del sondeo clínico (sin PII; sin metadatos reversibles).  
- **Principio de mínima retención**: guardar solo agregados geotemporales.  
- **Consentimiento y avisos**: política visible, *opt-in* para contactos.  
- **Legal**: apego a marcos locales (p. ej., Ley General de Protección de Datos Personales en Posesión de Sujetos Obligados, si aplica).  
- **Calidad/validación**: etiquetas de *confianza* por fuente; no usar señales sociales como diagnóstico, sino como **complemento** contextual.  
- **Trazabilidad**: bitácoras de ingestión, versiones de dataset y de reglas de alertas.

---

## 9) Reglas de decisión y alertas (MVP)

- **Incremento súbito** en casos oficiales: Δ≥10–20% vs. media móvil 14d.  
- **Señal social**: pico de menciones relevante + sentimiento negativo sostenido.  
- **Cruce oficial–social**: si ambas crecen en ≤7–14 días, elevar prioridad.  
- **Debounce**: evitar spam de alertas con ventanas de calma (cooldown).  
- **Justificación**: cada alerta muestra regla, ventana, umbral y series involucradas.

> En V1, ampliar con z-score, STL, CUSUM y pruebas de cambio de punto.

---

## 10) Flujo de datos (alto nivel)

1) **Ingesta**: APIs (INEGI, tableros/CSV oficiales), scraping ligero de boletines (PDF/HTML), y *stream* social (si aplica).  
2) **Normalización**: estandarizar fechas, claves geo (INEGI), nombres de morbilidad; control de duplicados y *schema mapping*.  
3) **Almacenamiento**: base relacional (PostgreSQL/PostGIS) + colecciones no estructuradas (MongoDB) para sociales.  
4) **Capa analítica**: agregaciones por entidad/semana; cálculo de KPIs; sentimiento; correlaciones.  
5) **Presentación**: API de lectura + dashboard (web) + generación de boletín.

---

## 11) Stack sugerido (MVP)

- **Ingesta/ETL**: Python (requests), Pandas/NumPy; Airflow (o *cron* + Papermill/Prefect para MVP).  
- **Análisis**: Scikit-learn (clasificación relevancia), NLTK (sentimiento), GeoPandas/Folium (mapas).  
- **Almacenamiento**: PostgreSQL + PostGIS; MongoDB (social).  
- **Frontend**: Dash/Plotly (rápido para MVP) con posibilidad de migrar a React/Leaflet en V1.  
- **Empaquetado**: Docker; despliegue simple en un VPS o servicio PaaS.

---

## 12) Calidad y observabilidad

- **Monitoreo**: métricas de pipeline (éxito, duración, latencia), *healthchecks* de endpoints, logs centralizados.  
- **Pruebas**: unitarias (transformaciones), de contrato (APIs), *visual regression* (capturas del dashboard), *smoke tests* tras cada actualización.  
- **Datos**: pruebas de *schema*, valores esperados/permitidos, densidad temporal, *freshness*.

---

## 13) Riesgos y mitigaciones (resumen)

- **Retrasos/fallos en datos oficiales** → fuentes alternativas estatales; modo degradado.  
- **Baja participación en sondeo** → incentivos simbólicos/comunidad; UX de 30–60 s.  
- **Ruido o datos falsos en redes** → filtros de relevancia, *whitelists*, verificación cruzada.  
- **Cambios en APIs** → adaptadores por proveedor; *feature flags*; pruebas de integración.

---

## 14) Roadmap y entregables

**Fase 0 – Planificación (≈1 mes)**  
- Afinar módulos; UI/UX de MVP; registro de nombre y branding.

**Fase 1 – Infraestructura de datos (≈1.5 meses)**  
- Conectar/automatizar ingestas oficiales; *backfill* y primeros KPIs.

**Fase 2 – Dashboard básico (≈1.5 meses)**  
- Vistas: KPIs, serie temporal, mapa; filtros clave.

**Fase 3 – Sondeo clínico/social (≈1 mes)**  
- Formulario + almacenamiento; *prototype* de monitoreo público de redes.

**Fase 4 – Boletín y alertas (≈1 mes)**  
- Plantilla de boletín; reglas de alertas; notificaciones.

**Fase 5 – Piloto (≈1 mes)**  
- Pruebas con usuarios clínicos; instrumentación de feedback.

**Fase 6 – Lanzamiento inicial (≈1 mes)**  
- Difusión e inserción institucional; soporte mínimo.

> *Hitos de salida de cada fase*: build estable, checklist de QA, demo, *changelog* y lecciones aprendidas.

---

## 15) Playbook operativo para el **IA Builder** (cómo construir)

**A. Preparación**
1. Crear repos: `episcopio-ingesta`, `episcopio-analitica`, `episcopio-dashboard`, `episcopio-infra` (IaC).  
2. Definir `.env` (tokens/keys) vía *secrets manager*; jamás *commitear* secretos.  
3. Plantillas de *issue/PR* y flujos CI mínimos (lint, tests, build).  

**B. Datos**
1. Implementar conectores: INEGI, DGE/SINAVE (CSV/HTML/PDF→tabla), CONACYT (si aplica).  
2. Estandarizar claves geo (INEGI), fechas ISO, morbilidades (catálogo).  
3. Persistir agregados por `anio/semana`, `entidad`, `morbilidad`.  

**C. Señales sociales / sondeo**
1. Formularios: campos mínimos (libres de PII), *rate limit* y CAPTCHA.  
2. Relevancia social: diccionario de keywords/hashtags; clasificador binario (relevante/no).  
3. Sentimiento: *baseline* (NLTK) + ventana móvil de estabilidad.  

**D. Alertas y boletín**
1. Reglas declarativas (YAML) con umbrales y ventanas.  
2. Render del boletín con plantilla `Jinja2` (HTML + texto).  
3. Envío por correo o descarga; registro de alertas en tabla dedicada.

**E. Dashboard**
1. Home con KPIs + mini feed de alertas.  
2. Pestañas: "Oficial", "Social/Sondeo", "Mapa", "Boletín".  
3. Filtros persistentes y exportaciones.  

**F. Calidad/Seguridad**
1. Pruebas de datos, *canary runs*, *rollback* simple.  
2. Roles (admin/lectura), *rate limiting*, CORS y CSP básicos.  
3. Telemetría de uso (anónima) para iterar UX.

---

## 16) Criterios de aceptación por módulo (MVP)

- **Ingesta oficial**: ≥1 fuente federal + ≥1 estatal; latencia <24 h; *freshness* visible.  
- **Serie temporal y mapa**: responden a filtros en <1 s con dataset de prueba.  
- **Señales sociales**: pipeline básico de menciones + sentimiento y *blacklist* de ruido.  
- **Boletín**: se genera con 1 clic o por cron; contiene KPIs, highlights y recomendaciones.  
- **Alertas**: pueden activarse/desactivarse por regla y registran evidencia.

---

## 17) Branding y comunicación

- **Nombre**: *Episcopio*.  
- **Identidad**: isologo de “ojo + dato”.  
- **Paleta**: verde-azulado/cian + grises; acentos naranjas para alertas.  
- **Tono**: profesional, claro, centrado en utilidad clínica.  
- **Materiales**: portada del dashboard, mini infografías de uso y política de datos.

---

## 18) Roadmap de evolución (post V1)

- Migración progresiva del front a **React + Leaflet**.  
- Modelos de **detección temprana** más sofisticados (cambio de régimen, *nowcasting*).  
- **API pública** con *rate limits* y *API keys*.  
- **Internacionalización** a Centroamérica; catálogo multilingüe.  
- Integración con **mensajería** (WhatsApp/Email) para alertas suscritas.

---

## 19) Glosario

- **Caso confirmado/activo/defunción**: según definiciones operativas de SSA/DGE.  
- **Sondeo clínico**: reporte voluntario, anónimo, sin PII, de observaciones de terreno.  
- **Señal social**: menciones públicas relacionadas a salud, sin inferir diagnósticos.  
- **KPIs**: indicadores clave del panel y operación.  
- **Freshness**: tiempo desde ingesta hasta disponibilidad en el dashboard.

---

## 20) Apéndice — Catálogo de tecnologías (para el Documento 2)

**Recolección**: Python requests; Tweepy/Facebook SDK (si aplica).  
**Procesamiento**: Pandas/NumPy; Airflow/Prefect; limpieza/normalización.  
**Análisis**: Scikit-learn, NLTK; GeoPandas/Folium; correlaciones.  
**Base de datos**: PostgreSQL/PostGIS; MongoDB (social).  
**Visualización**: Plotly/Matplotlib/Seaborn; Dash/Plotly Express.  
**DevOps**: Docker; jobs con *cron*; Papermill para notebooks ejecutables; Voilà (publicación notebook como app).  

> El **Documento 2** detallará APIs/Endpoints, esquemas de tablas/colecciones, diccionarios de datos, configuraciones de despliegue e infraestructura (IaC).

---

### Fin del Documento 1

