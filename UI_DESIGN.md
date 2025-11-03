# Episcopio - Diseño de Interfaz de Usuario

## 🎨 Descripción del Nuevo Diseño

La nueva interfaz de Episcopio ha sido completamente rediseñada con un enfoque moderno, minimalista y altamente responsivo.

## 🌈 Esquema de Colores

### Paleta Principal

```css
🟣 Primary: #667eea (Azul-púrpura brillante)
🟪 Secondary: #764ba2 (Púrpura profundo)
🟢 Success: #27ae60 (Verde esmeralda)
🟠 Warning: #f39c12 (Naranja cálido)
🔴 Danger: #e74c3c (Rojo vibrante)
🔵 Info: #3498db (Azul cielo)
⚪ Light: #ecf0f1 (Gris claro neutro)
⚫ Dark: #2c3e50 (Azul oscuro profundo)
🔘 Text: #7f8c8d (Gris medio)
```

### Gradientes

**Primario (Botones, Headers):**
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

**Fondo General:**
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

**Alertas:**
```css
background: linear-gradient(135deg, #fff3cd 0%, #ffe8a1 100%);
```

## 📱 Componentes Principales

### 1. Header (Encabezado)

**Características:**
- Fondo blanco con sombra elevada
- Logo con gradiente en el texto
- Subtítulo descriptivo
- Badge de modo de datos (muestra/real)
- Botón de configuración
- Totalmente responsivo

**Elementos:**
```
┌─────────────────────────────────────────────────────┐
│ 🏥 Episcopio          [🎭 Modo: Datos] [⚙️ Config] │
│ Tomando el pulso epidemiológico de México           │
└─────────────────────────────────────────────────────┘
```

### 2. Sección de Filtros

**Características:**
- Grid responsivo de 2 columnas
- Dropdowns con emojis descriptivos
- Botón de actualización full-width con gradiente
- Espaciado generoso

**Layout:**
```
┌─────────────────────────────────────────┐
│ 🔍 Filtros                              │
├─────────────────────────────────────────┤
│ [Entidad] 🌴        [Morbilidad] 🦠    │
│ [Yucatán ▼]         [COVID-19 ▼]       │
│                                         │
│ [🔄 Actualizar Dashboard              ]│
└─────────────────────────────────────────┘
```

### 3. Tarjetas KPI

**Características:**
- Grid adaptativo (3 columnas en desktop, 1 en móvil)
- Barra superior con gradiente
- Números grandes y legibles
- Indicadores de cambio porcentual
- Efecto hover (elevación)

**Diseño de Tarjeta:**
```
┌─────────────────────────────┐ ← Barra de color (4px)
│ 📊 CASOS TOTALES            │
│                             │
│      12,500                 │ ← Número grande con gradiente
│                             │
│ ↑ 8% vs semana anterior     │ ← Indicador de cambio
└─────────────────────────────┘
```

**Grid Responsivo:**

Desktop (3 columnas):
```
┌─────────┬─────────┬─────────┐
│ Casos   │ Activos │Defuncio │
│ Totales │         │  nes    │
└─────────┴─────────┴─────────┘
```

Móvil (1 columna):
```
┌─────────┐
│ Casos   │
│ Totales │
├─────────┤
│ Activos │
├─────────┤
│Defuncio │
│  nes    │
└─────────┘
```

### 4. Gráficos

**Serie Temporal:**
- Fondo gris claro (#f8f9fa)
- Línea principal en azul-púrpura (#667eea)
- Marcadores en puntos de datos
- Título descriptivo
- Eje x: Fechas
- Eje y: Número de casos

**Visualización:**
```
📈 Serie Temporal - Casos Confirmados
┌──────────────────────────────────┐
│                        ╱╲         │
│                      ╱   ╲        │
│                    ╱      ╲       │
│                  ╱         ╲      │
│                ╱            ╲     │
│  ────────────                ─────│
│  Enero    Febrero    Marzo        │
└──────────────────────────────────┘
```

**Análisis de Sentimiento:**
- Gráfico combinado (barras + línea)
- Barras verdes para menciones
- Línea roja para sentimiento
- Doble eje y (izquierda y derecha)

```
💬 Análisis de Sentimiento en Redes Sociales
┌──────────────────────────────────┐
│ ▮ ▮▮▮    ▮▮▮ ▮      ─┐          │
│ ▮ ▮▮▮    ▮▮▮ ▮    ╱  │Sentimiento
│ ▮ ▮▮▮    ▮▮▮ ▮  ╱    │          │
│ ▮ ▮▮▮    ▮▮▮ ▮╱       │          │
└─────────────────┬────────────────┘
                  Menciones
```

### 5. Alertas

**Características:**
- Fondo con gradiente amarillo
- Borde izquierdo destacado
- Icono de alerta (⚠️)
- Información estructurada
- Efecto de desplazamiento al hover

**Diseño:**
```
⚠️ Alertas Activas
┌────────────────────────────────────┐
│┃ ⚠️ Incremento Súbito              │
│┃ Regla: a1 | Estado: activa        │
│┃ Creada: 2025-01-15T10:30:00Z      │
└────────────────────────────────────┘
```

### 6. Modal de Configuración

**Características:**
- Overlay con blur en el fondo
- Animación de entrada suave
- Diseño limpio y organizado
- Warning box destacado
- Inputs con borde y focus states
- Botones con gradientes

**Layout:**
```
╔════════════════════════════════════╗
║ ⚙️ Configuración de API Keys      ║
╟────────────────────────────────────╢
║ Descripción...                     ║
║                                    ║
║ ⚠️ Advertencia de Seguridad        ║
║                                    ║
║ INEGI Token:                       ║
║ [_________________________]        ║
║                                    ║
║ Twitter Bearer Token:              ║
║ [_________________________]        ║
║                                    ║
║ (más campos...)                    ║
║                                    ║
║     [Guardar] [Usar Muestra]      ║
╚════════════════════════════════════╝
```

### 7. Footer

**Características:**
- Fondo blanco con sombra
- Texto centrado
- Información de copyright
- Link al notebook

```
┌─────────────────────────────────────┐
│ © 2025 Episcopio - Monitoreo       │
│ Epidemiológico                      │
│                                     │
│ 📓 Explora los procesos ETL en el  │
│ Jupyter Notebook incluido           │
└─────────────────────────────────────┘
```

## 📐 Responsividad

### Breakpoints

```css
Desktop:  > 768px
Tablet:   480px - 768px
Móvil:    < 480px
```

### Adaptaciones por Dispositivo

#### Desktop (> 768px)
- Grid de 3 columnas para KPIs
- Header horizontal
- Espaciado generoso (padding: 25-30px)
- Todos los elementos visibles

#### Tablet (480px - 768px)
- Grid de 2 columnas para KPIs (si hay espacio)
- Header puede apilar elementos
- Padding moderado (padding: 20px)

#### Móvil (< 480px)
- Grid de 1 columna para KPIs
- Header completamente apilado
- Padding reducido (padding: 15-20px)
- Botones full-width
- Fuentes más pequeñas
- Modal optimizado

## 🎭 Interactividad

### Efectos Hover

**Tarjetas KPI:**
```css
hover: {
  transform: translateY(-5px);
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
}
```

**Botones:**
```css
hover: {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}
```

**Alertas:**
```css
hover: {
  transform: translateX(5px);
  box-shadow: 0 5px 15px rgba(243, 156, 18, 0.2);
}
```

### Transiciones

Todas las transiciones usan:
```css
transition: all 0.3s ease;
```

Esto proporciona movimientos suaves y naturales.

### Focus States

Los inputs tienen estados de focus visibles:
```css
focus: {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}
```

## 🔤 Tipografía

### Fuente
```css
font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
```

### Tamaños

```css
Título principal: 2.5rem (40px)
Título sección: 1.3rem (21px)
Texto normal: 1rem (16px)
Texto pequeño: 0.85rem (14px)
Badge/botón: 0.9-0.95rem (15px)
```

### Pesos

```css
Bold (700): Títulos principales
Semi-bold (600): Subtítulos, labels
Normal (400): Texto regular
```

## 🌟 Elementos Destacados

### Gradientes de Texto

Los títulos principales usan gradientes:
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
```

### Sombras (Box Shadow)

**Tarjetas normales:**
```css
box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
```

**Tarjetas al hover:**
```css
box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
```

**Modal:**
```css
box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
```

**Botones:**
```css
box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
```

### Border Radius

```css
Tarjetas grandes: 15px
Botones: 10px (normales), 25px (pills)
Inputs: 10px
Modal: 20px
```

## 📊 Gráficos Plotly

### Configuración de Tema

```python
fig.update_layout(
    plot_bgcolor='#f8f9fa',      # Fondo claro
    paper_bgcolor='white',         # Fondo del papel
    font=dict(
        family="'Segoe UI'",
        size=12,
        color='#2c3e50'
    ),
    xaxis=dict(
        showgrid=True,
        gridcolor='#e0e0e0'
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor='#e0e0e0'
    )
)
```

### Colores de Líneas

```python
Primary: '#667eea'
Success: '#27ae60'
Danger: '#e74c3c'
```

## 🎯 Mejores Prácticas Implementadas

### Accesibilidad
- ✅ Contraste de colores WCAG AA
- ✅ Tamaños de fuente legibles
- ✅ Espaciado generoso entre elementos
- ✅ Focus states visibles

### Performance
- ✅ CSS modular y optimizado
- ✅ Imágenes de tamaño apropiado
- ✅ Carga diferida de gráficos
- ✅ Uso de transforms para animaciones

### UX
- ✅ Feedback visual inmediato
- ✅ Estados de carga claros
- ✅ Mensajes de error descriptivos
- ✅ Flujo de navegación intuitivo

### Responsive
- ✅ Mobile-first approach
- ✅ Breakpoints bien definidos
- ✅ Grid layouts flexibles
- ✅ Touch targets apropiados (mínimo 44x44px)

## 🔮 Mejoras Futuras Sugeridas

1. **Temas:** Modo claro/oscuro
2. **Animaciones:** Más microinteracciones
3. **Personalización:** Permitir cambiar colores
4. **Accesibilidad:** Soporte completo para screen readers
5. **Exportar:** Descargar gráficos como PNG/PDF
6. **Compartir:** Enlaces directos a vistas específicas

## 📸 Capturas de Pantalla Simuladas

### Desktop View
```
┌────────────────────────────────────────────────────────────┐
│ Header con gradiente                                       │
├────────────────────────────────────────────────────────────┤
│ Filtros (2 columnas)                                       │
├──────────────┬──────────────┬──────────────────────────────┤
│ KPI Card 1   │ KPI Card 2   │ KPI Card 3                  │
├──────────────┴──────────────┴──────────────────────────────┤
│ Gráfico Serie Temporal (ancho completo)                    │
├────────────────────────────────────────────────────────────┤
│ Gráfico Sentimiento (ancho completo)                       │
├────────────────────────────────────────────────────────────┤
│ Alertas (ancho completo)                                   │
├────────────────────────────────────────────────────────────┤
│ Footer                                                      │
└────────────────────────────────────────────────────────────┘
```

### Mobile View
```
┌──────────────────┐
│ Header (apilado) │
├──────────────────┤
│ Filtros          │
│ (1 columna)      │
├──────────────────┤
│ KPI Card 1       │
├──────────────────┤
│ KPI Card 2       │
├──────────────────┤
│ KPI Card 3       │
├──────────────────┤
│ Gráfico 1        │
├──────────────────┤
│ Gráfico 2        │
├──────────────────┤
│ Alertas          │
├──────────────────┤
│ Footer           │
└──────────────────┘
```

---

**Fecha:** 2025-01-03  
**Versión del diseño:** 2.0.0  
**Framework:** Dash/Plotly + CSS3
