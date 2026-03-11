# 🚀 API FastAPI para Práctica de JWT

API completa para practicar autenticación JWT con **curl** y entender cómo funciona el flujo de tokens de acceso y refresh.

---

## 📋 Requisitos

- Python 3.11+
- curl
- jq (opcional, para formatear JSON)

---

## 🛠️ Instalación

```bash
# Clonar o navegar al directorio
cd DWES-UT06-FastAPI-Exercises

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt
```

---

## ▶️ Iniciar la API

```bash
uvicorn main:app --reload --port 8000
```

Verifica que funciona:
```bash
curl http://localhost:8000/
```

---

## 👤 Usuarios de Prueba

| Usuario | Contraseña | Rol | Permisos |
|---------|-----------|-----|----------|
| `profesor1` | `Pass1234!` | teacher | Ver socios, crear socios |
| `admin1` | `Admin5678!` | admin | Todo lo anterior + eliminar socios + seed data |
| `root` | `Root9999!` | root | Todo + ver lista de usuarios |

---

## 🧪 Ejercicios Prácticos con curl

### **Nivel 1: Login Básico**

#### 1.1 Login y guardar tokens en variables

```bash
# Login y extraer tokens
RESPONSE=$(curl -s -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{"username":"profesor1","password":"Pass1234!"}')

echo $RESPONSE | jq .

# Extraer tokens a variables
ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access_token')
REFRESH_TOKEN=$(echo $RESPONSE | jq -r '.refresh_token')

echo "Access Token: $ACCESS_TOKEN"
echo "Refresh Token: $REFRESH_TOKEN"
```

**Qué observar:**
- El `access_token` expira en 15 minutos (900 segundos)
- El `refresh_token` permite obtener un nuevo access_token sin volver a loguearse

---

### **Nivel 2: Peticiones Autenticadas**

#### 2.1 Ver mi perfil

```bash
curl -s http://localhost:8000/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

**Respuesta esperada:**
```json
{
  "username": "profesor1",
  "full_name": "Ana García",
  "role": "teacher",
  "token_data": {
    "sub": "profesor1",
    "exp": 1741701234,
    "iat": 1741700334,
    "role": "teacher"
  }
}
```

#### 2.2 Crear un socio (POST)

```bash
curl -s -X POST http://localhost:8000/socios \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nombre":"María López","email":"maria@ejemplo.com","dni":"12345678Z"}' | jq .
```

**Validaciones:**
- El DNI debe tener 8 dígitos + 1 letra (ej: `12345678Z`)
- El email debe ser válido
- El nombre debe tener entre 2 y 100 caracteres

#### 2.3 Listar socios

```bash
curl -s "http://localhost:8000/socios?skip=0&limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

#### 2.4 Obtener un socio específico

```bash
curl -s http://localhost:8000/socios/1 \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

---

### **Nivel 3: Manejo de Errores 401/403**

#### 3.1 Sin token (401 Unauthorized)

```bash
curl -s -w "\nHTTP Status: %{http_code}\n" http://localhost:8000/me
```

**Esperado:** `HTTP Status: 401`

#### 3.2 Token inválido (401)

```bash
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer token.falso.invalido" \
  http://localhost:8000/me
```

**Esperado:** `HTTP Status: 401`

#### 3.3 Token expirado (401)

Espera 15 minutos después del login o modifica el token manualmente:

```bash
# Usar un token expirado (ejemplo)
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  http://localhost:8000/me
```

**Esperado:** `HTTP Status: 401` con mensaje "Token expirado"

---

### **Nivel 4: Refresh Token**

#### 4.1 Obtener nuevo access_token con refresh_token

```bash
NEW_RESPONSE=$(curl -s -X POST http://localhost:8000/token/refresh \
  -H "X-Refresh-Token: $REFRESH_TOKEN")

echo $NEW_RESPONSE | jq .

# Extraer el nuevo access_token
NEW_ACCESS=$(echo $NEW_RESPONSE | jq -r '.access_token')
NEW_REFRESH=$(echo $NEW_RESPONSE | jq -r '.refresh_token')
```

**Importante:** Cada vez que usas el refresh_token, se genera uno **nuevo** (rotación de tokens).

#### 4.2 Verificar que el nuevo token funciona

```bash
curl -s http://localhost:8000/me \
  -H "Authorization: Bearer $NEW_ACCESS" | jq .
```

#### 4.3 Usar refresh_token viejo (debe fallar)

```bash
curl -s -w "\nHTTP Status: %{http_code}\n" -X POST \
  -H "X-Refresh-Token: $REFRESH_TOKEN" \
  http://localhost:8000/token/refresh
```

**Nota:** Como se generó uno nuevo, el anterior ya no es válido (depende de implementación, en esta API ambos funcionan, pero en producción se invalida el anterior).

---

### **Nivel 5: Control de Acceso por Roles (RBAC)**

#### 5.1 Login como admin

```bash
ADMIN_RESP=$(curl -s -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin1","password":"Admin5678!"}')

ADMIN_TOKEN=$(echo $ADMIN_RESP | jq -r '.access_token')
echo "Admin Token: $ADMIN_TOKEN"
```

#### 5.2 Intentar acceso admin con token de profesor (403 Forbidden)

```bash
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  http://localhost:8000/admin/users
```

**Esperado:** `HTTP Status: 403` - "Se requiere rol: ['root']"

#### 5.3 Acceso correcto con admin a eliminar socios

```bash
curl -s -X DELETE http://localhost:8000/socios/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .
```

#### 5.4 Login como root y acceso total

```bash
ROOT_RESP=$(curl -s -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{"username":"root","password":"Root9999!"}')

ROOT_TOKEN=$(echo $ROOT_RESP | jq -r '.access_token')

# Ver todos los usuarios (solo root)
curl -s http://localhost:8000/admin/users \
  -H "Authorization: Bearer $ROOT_TOKEN" | jq .
```

---

### **Nivel 6: Debug y Análisis de Tokens**

#### 6.1 Ver información del token decodificado

```bash
curl -s http://localhost:8000/debug/token-info \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

**Respuesta:**
```json
{
  "decoded_payload": {
    "sub": "profesor1",
    "exp": 1741701234,
    "iat": 1741700334,
    "role": "teacher"
  },
  "expires_at": "2025-03-11T15:13:54",
  "issued_at": "2025-03-11T14:58:54",
  "time_remaining_seconds": 895,
  "note": "En producción, nunca expongas la SECRET_KEY"
}
```

#### 6.2 Generar datos de prueba (solo admin/root)

```bash
curl -s -X POST "http://localhost:8000/admin/seed-socios?count=5" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .
```

---

## 🔧 Script de Pruebas Automatizado

Ejecuta todas las pruebas de una vez:

```bash
chmod +x test_jwt.sh
./test_jwt.sh
```

El script realiza:
1. Health check
2. Login como profesor
3. Obtener perfil
4. Crear socio
5. Prueba sin token (401)
6. Prueba token inválido (401)
7. Refresh token
8. Login como admin y acceso a ruta protegida
9. Prueba de acceso prohibido (403)

---

## 📚 Resumen de Endpoints

### Públicos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Información de la API |
| GET | `/health` | Health check |
| POST | `/token` | Login - obtiene tokens |
| POST | `/token/refresh` | Renueva access_token |

### Protegidos (requieren Bearer token)
| Método | Endpoint | Rol requerido | Descripción |
|--------|----------|---------------|-------------|
| GET | `/me` | Cualquiera | Ver perfil |
| GET | `/socios` | Cualquiera | Listar socios |
| POST | `/socios` | Cualquiera | Crear socio |
| GET | `/socios/{id}` | Cualquiera | Ver socio |
| DELETE | `/socios/{id}` | admin, root | Eliminar socio |
| GET | `/admin/users` | root | Listar usuarios |
| POST | `/admin/seed-socios` | admin, root | Generar datos |
| GET | `/debug/token-info` | Cualquiera | Info del token |

---

## 🔐 Estructura del JWT

Un JWT tiene 3 partes separadas por puntos (`.`):

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJwcm9mZXNvciIsInJvbGUiOiJ0ZWFjaGVyIn0.firma
    ↑_____________________↑ ↑_________________________________↑ ↑_____↑
           HEADER                     PAYLOAD                      SIGNATURE
```

**Header:** Algoritmo y tipo
```json
{"alg":"HS256","typ":"JWT"}
```

**Payload:** Datos (claims)
```json
{
  "sub": "profesor1",
  "role": "teacher",
  "iat": 1741700334,
  "exp": 1741701234
}
```

**Signature:** Firma con SECRET_KEY

---

## 📝 Notas Importantes

1. **Expiración:** El `access_token` dura 15 minutos, el `refresh_token` 7 días
2. **HTTPS en producción:** Siempre usar HTTPS para transmitir tokens
3. **Almacenamiento:** Nunca guardes tokens en localStorage (vulnerable a XSS), usa httpOnly cookies
4. **SECRET_KEY:** En producción, usa variables de entorno y una clave fuerte


