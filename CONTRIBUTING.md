# Guía de Contribución - Episcopio

¡Gracias por tu interés en contribuir a Episcopio! Esta guía te ayudará a empezar.

## 📋 Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [¿Cómo Puedo Contribuir?](#cómo-puedo-contribuir)
- [Configuración del Entorno de Desarrollo](#configuración-del-entorno-de-desarrollo)
- [Proceso de Desarrollo](#proceso-de-desarrollo)
- [Estándares de Código](#estándares-de-código)
- [Commits y Pull Requests](#commits-y-pull-requests)
- [Pruebas](#pruebas)
- [Documentación](#documentación)

## 🤝 Código de Conducta

### Nuestro Compromiso

Nos comprometemos a hacer de la participación en este proyecto una experiencia libre de acoso para todos, independientemente de edad, tamaño corporal, discapacidad, etnia, identidad y expresión de género, nivel de experiencia, nacionalidad, apariencia personal, raza, religión o identidad y orientación sexual.

### Comportamientos Esperados

- Usar lenguaje acogedor e inclusivo
- Respetar puntos de vista y experiencias diferentes
- Aceptar críticas constructivas con gracia
- Enfocarse en lo mejor para la comunidad
- Mostrar empatía hacia otros miembros

### Comportamientos Inaceptables

- Uso de lenguaje o imágenes sexualizadas
- Comentarios insultantes o despectivos (trolling)
- Acoso público o privado
- Publicar información privada de otros sin permiso
- Conducta inapropiada en un entorno profesional

## 💡 ¿Cómo Puedo Contribuir?

### Reportar Bugs

Si encuentras un bug, por favor abre un issue con:

- **Título descriptivo**: Resume el problema en una línea
- **Pasos para reproducir**: Detalla cómo reproducir el bug
- **Comportamiento esperado**: Qué debería pasar
- **Comportamiento actual**: Qué está pasando
- **Contexto**: OS, versión de Docker, logs relevantes
- **Screenshots**: Si aplica

**Template de Bug Report:**

```markdown
**Descripción del Bug**
Una descripción clara del problema.

**Para Reproducir**
1. Ve a '...'
2. Haz clic en '...'
3. Ve el error

**Comportamiento Esperado**
Lo que debería suceder.

**Screenshots**
Si aplica, añade screenshots.

**Entorno:**
 - OS: [e.g. Ubuntu 22.04]
 - Docker: [e.g. 24.0.5]
 - Versión: [e.g. 1.0.0-mvp]

**Logs**
```
Pega logs relevantes aquí
```

**Contexto Adicional**
Añade cualquier otro contexto sobre el problema.
```

### Sugerir Mejoras

Para sugerir nuevas funcionalidades o mejoras:

1. Verifica que no exista ya un issue similar
2. Abre un nuevo issue con tag `enhancement`
3. Describe claramente:
   - La funcionalidad que propones
   - Por qué sería útil
   - Cómo debería funcionar
   - Posibles implementaciones

### Contribuir con Código

1. **Fork** el repositorio
2. **Clona** tu fork localmente
3. **Crea una rama** para tu feature
4. **Desarrolla** tu feature
5. **Prueba** tu código
6. **Commit** tus cambios
7. **Push** a tu fork
8. **Abre un Pull Request**

## 🛠️ Configuración del Entorno de Desarrollo

### Requisitos Previos

- Python 3.11+
- Docker y Docker Compose
- Git
- (Opcional) PostgreSQL local para desarrollo

### Setup Local

```bash
# Clonar el repositorio
git clone https://github.com/TU_USUARIO/Episcopio.git
cd Episcopio

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Instalar dependencias de desarrollo
pip install flake8 black pytest pytest-cov

# Copiar configuración de ejemplo
cp config/secrets.sample.yaml config/secrets.local.yaml
cp infra/.env.example infra/.env
```

### Ejecutar en Modo Desarrollo

```bash
# Iniciar servicios con Docker Compose
cd infra
docker-compose up -d

# Inicializar base de datos
cd ..
make init-db
make seed-db

# Ejecutar API en modo desarrollo
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# En otra terminal, ejecutar Dashboard
cd dashboard
python app.py
```

## 🔄 Proceso de Desarrollo

### 1. Crear una Rama

```bash
git checkout -b feature/nombre-de-tu-feature
# o
git checkout -b fix/nombre-del-bug
```

Convenciones de nombres:
- `feature/` - Nueva funcionalidad
- `fix/` - Corrección de bug
- `docs/` - Cambios en documentación
- `refactor/` - Refactorización sin cambiar funcionalidad
- `test/` - Añadir o mejorar tests
- `chore/` - Mantenimiento, dependencias, etc.

### 2. Desarrollar

- Escribe código limpio y legible
- Comenta código complejo
- Sigue los estándares de código (ver abajo)
- Añade tests para nueva funcionalidad

### 3. Probar

```bash
# Validar configuración
make test

# Ejecutar linting
make lint

# Ejecutar tests (cuando estén implementados)
pytest

# Verificar cobertura
pytest --cov=.
```

### 4. Commit

```bash
# Añadir archivos
git add .

# Commit con mensaje descriptivo
git commit -m "feat: añadir filtro por municipio en dashboard"
```

## 📝 Estándares de Código

### Python

#### PEP 8
Seguir [PEP 8](https://pep8.org/) para estilo de código Python.

```bash
# Verificar con flake8
flake8 api/ dashboard/ analytics/ etl/ ingesta/

# Formatear con black (opcional)
black api/ dashboard/ analytics/ etl/ ingesta/
```

#### Nombres

- **Módulos/paquetes**: `minusculas_con_guion_bajo`
- **Clases**: `PascalCase`
- **Funciones/variables**: `minusculas_con_guion_bajo`
- **Constantes**: `MAYUSCULAS_CON_GUION_BAJO`

#### Docstrings

```python
def funcion_ejemplo(parametro1, parametro2):
    """
    Breve descripción de la función.
    
    Args:
        parametro1 (tipo): Descripción del parámetro
        parametro2 (tipo): Descripción del parámetro
    
    Returns:
        tipo: Descripción del valor retornado
    
    Raises:
        TipoError: Cuándo se lanza
    
    Example:
        >>> funcion_ejemplo("valor1", 42)
        resultado_esperado
    """
    pass
```

### SQL

- Palabras clave en MAYÚSCULAS: `SELECT`, `FROM`, `WHERE`
- Nombres de tablas/columnas en minúsculas: `geo_entidad`, `casos`
- Indentar subconsultas
- Usar nombres descriptivos

```sql
SELECT 
    e.nombre,
    SUM(s.casos) AS total_casos
FROM geo_entidad e
    JOIN serie_oficial s ON e.cve_ent = s.cve_ent
WHERE s.fecha >= '2025-01-01'
GROUP BY e.nombre
ORDER BY total_casos DESC;
```

### YAML

- 2 espacios para indentación
- Comentarios para secciones complejas
- Claves en snake_case

```yaml
# Configuración de alertas
alertas:
  window_days: 14
  threshold: 0.2
  
  # Reglas específicas
  reglas:
    - id: a1
      nombre: "Incremento súbito"
```

## 💬 Commits y Pull Requests

### Mensajes de Commit

Formato: `<tipo>: <descripción>`

**Tipos:**
- `feat`: Nueva funcionalidad
- `fix`: Corrección de bug
- `docs`: Cambios en documentación
- `style`: Formato, punto y coma faltantes, etc.
- `refactor`: Refactorización de código
- `test`: Añadir tests
- `chore`: Mantenimiento

**Ejemplos:**
```
feat: añadir endpoint para boletines por fecha
fix: corregir cálculo de promedio móvil en KPIs
docs: actualizar guía de instalación en README
refactor: separar lógica de alertas en funciones más pequeñas
test: añadir tests para normalizador de fechas
chore: actualizar dependencias de FastAPI
```

### Pull Requests

**Título:** Usa el mismo formato que los commits

**Descripción:** Debe incluir:

```markdown
## Descripción
Breve descripción de los cambios.

## Tipo de Cambio
- [ ] Bug fix (non-breaking change que arregla un issue)
- [ ] Nueva funcionalidad (non-breaking change que añade funcionalidad)
- [ ] Breaking change (fix o feature que causaría que funcionalidad existente no funcione como se esperaba)
- [ ] Cambio de documentación

## ¿Cómo se ha probado?
Describe las pruebas que realizaste.

## Checklist
- [ ] Mi código sigue los estándares de este proyecto
- [ ] He realizado self-review de mi código
- [ ] He comentado mi código en áreas difíciles
- [ ] He actualizado la documentación
- [ ] Mis cambios no generan warnings
- [ ] He añadido tests que prueban mi fix/feature
- [ ] Tests nuevos y existentes pasan localmente
- [ ] He actualizado el CHANGELOG.md

## Screenshots (si aplica)
Añade screenshots para demostrar cambios visuales.
```

### Proceso de Review

1. Tu PR será revisado por un maintainer
2. Puede que se soliciten cambios
3. Realiza los cambios solicitados
4. Una vez aprobado, será merged a main

## 🧪 Pruebas

### Escribir Tests

```python
# tests/test_normaliza.py
import pytest
from etl.normaliza import estandarizar_fecha

def test_estandarizar_fecha_formato_slash():
    """Test normalización de fecha DD/MM/YYYY."""
    result = estandarizar_fecha("15/01/2025")
    assert result == "2025-01-15"

def test_estandarizar_fecha_ya_iso():
    """Test que fecha ISO no se modifica."""
    result = estandarizar_fecha("2025-01-15")
    assert result == "2025-01-15"
```

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Con cobertura
pytest --cov=.

# Test específico
pytest tests/test_normaliza.py

# Con verbose
pytest -v
```

## 📖 Documentación

### Actualizar Documentación

Si tus cambios afectan funcionalidad visible:

1. Actualiza el README.md si es necesario
2. Actualiza ARCHITECTURE.md para cambios arquitectónicos
3. Actualiza TESTING.md si añades tests
4. Añade entrada en CHANGELOG.md

### Escribir Documentación

- Usa Markdown para documentos
- Incluye ejemplos de código
- Añade screenshots para cambios visuales
- Explica el "por qué", no solo el "qué"

## 🏆 Reconocimiento

Los contributors serán reconocidos en:
- README.md (sección Contributors)
- CHANGELOG.md (por versión)
- GitHub contributors page

## ❓ Preguntas

Si tienes preguntas:

1. Revisa la [documentación](README.md)
2. Busca en [issues existentes](https://github.com/PedroRgz/Episcopio/issues)
3. Abre un nuevo issue con tag `question`

## 📜 Licencia

Al contribuir, aceptas que tus contribuciones serán licenciadas bajo la misma licencia MIT del proyecto.

---

**¡Gracias por contribuir a Episcopio!** 🎉

Cada contribución, sin importar cuán pequeña, ayuda a mejorar el monitoreo epidemiológico en México.
