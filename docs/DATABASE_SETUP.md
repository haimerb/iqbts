# Configuración de PostgreSQL para IQBTS

## Requisitos Previos

- PostgreSQL instalado y ejecutándose (versión 12 o superior)
- Python 3.9+ con el entorno virtual activado

## Pasos de Configuración

### 1. Instalar PostgreSQL

**Windows:**
- Descarga desde [postgresql.org](https://www.postgresql.org/download/windows/)
- Durante la instalación, recuerda la contraseña del usuario `postgres`

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install postgresql postgresql-contrib
```

### 2. Crear Base de Datos y Usuario

Abre `psql` (PostgreSQL CLI):

```bash
psql -U postgres
```

Ejecuta los siguientes comandos:

```sql
-- Crear usuario
CREATE USER iqbts_user WITH PASSWORD 'iqbts_password';

-- Crear base de datos
CREATE DATABASE iqbts_db OWNER iqbts_user;

-- Dar permisos
GRANT ALL PRIVILEGES ON DATABASE iqbts_db TO iqbts_user;

-- Para tablas futuras
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO iqbts_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO iqbts_user;
```

Sal de psql:
```sql
\q
```

### 3. Configurar Variables de Entorno

**Opción A: Usar archivo `.env`**

Copia `.env.example` a `.env` y edita con tus valores:

```bash
cp .env.example .env
```

Edita `.env`:
```
DB_HOST=localhost
DB_PORT=5432
DB_USER=iqbts_user
DB_PASSWORD=iqbts_password
DB_NAME=iqbts_db
```

**Opción B: Usar variables del sistema**

En Windows (PowerShell):
```powershell
[Environment]::SetEnvironmentVariable("DB_HOST", "localhost", "User")
[Environment]::SetEnvironmentVariable("DB_PORT", "5432", "User")
[Environment]::SetEnvironmentVariable("DB_USER", "iqbts_user", "User")
[Environment]::SetEnvironmentVariable("DB_PASSWORD", "iqbts_password", "User")
[Environment]::SetEnvironmentVariable("DB_NAME", "iqbts_db", "User")
```

### 4. Inicializar la Base de Datos

Ejecuta este script Python para crear las tablas:

```python
from src.servicios.database import init_db, test_connection

# Probar conexión
if test_connection():
    print("✓ Conexión a PostgreSQL exitosa")
    # Inicializar tablas
    init_db()
    print("✓ Tablas creadas correctamente")
else:
    print("✗ Error al conectar a PostgreSQL")
```

O desde la terminal:
```bash
python -c "from src.servicios.database import init_db, test_connection; test_connection() and init_db()"
```

### 5. Verificar la Instalación

```python
from src.servicios.database import get_session
from src.servicios.models import User

# Crear un usuario de prueba
session = get_session()
test_user = User(email="test@example.com", password_hash="hash123")
session.add(test_user)
session.commit()
print("✓ Usuario de prueba creado")
session.close()
```

## Uso en tu Aplicación

### En tu API Flask

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from src.servicios.database import get_engine

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://iqbts_user:iqbts_password@localhost/iqbts_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
```

### Consultas Básicas

```python
from src.servicios.database import get_session
from src.servicios.models import User, Trade

session = get_session()

# Crear
new_user = User(email="user@example.com", password_hash="hashed_pwd")
session.add(new_user)
session.commit()

# Leer
user = session.query(User).filter_by(email="user@example.com").first()

# Actualizar
user.is_active = False
session.commit()

# Eliminar
session.delete(user)
session.commit()

session.close()
```

## Troubleshooting

### "psycopg2: connection refused"
- Verifica que PostgreSQL está ejecutándose
- Verifica las credenciales en `.env`
- Verifica que la base de datos existe

### "FATAL: role 'iqbts_user' does not exist"
- Crea el usuario usando los comandos SQL anteriores

### "database 'iqbts_db' does not exist"
- Crea la base de datos usando `CREATE DATABASE iqbts_db`

## Migración de Datos (Futuro)

Para migraciones automáticas, considera usar [Alembic](https://alembic.sqlalchemy.org/):

```bash
pip install alembic
alembic init migrations
```

## Seguridad

⚠️ **IMPORTANTE**: 
- ¡NUNCA commits `.env` a Git!
- Usa contraseñas fuertes en producción
- Cambia `echo=False` a `echo=True` en `database.py` para debugging

## Documentación Útil

- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
- [psycopg2](https://www.psycopg.org/documentation/)
- [PostgreSQL](https://www.postgresql.org/docs/)
