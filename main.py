from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from typing import List, Optional
import time

from auth import (
    authenticate_user, create_access_token, create_refresh_token,
    decode_token, verify_refresh_token, get_user, fake_users_db,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
)
from models import Token, LoginRequest, SocioCreate, SocioResponse, User

app = FastAPI(
    title="JWT Practice API",
    description="API para practicar autenticación JWT con curl y Postman",
    version="1.0.0"
)

security = HTTPBearer(auto_error=False)

# Base de datos fake para socios
socios_db: List[dict] = []
socio_id_counter = 1


# Middleware para logging (educativo)
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    print(f"[{request.method}] {request.url.path} - {response.status_code} ({process_time:.3f}s)")
    return response


# ============ ENDPOINTS PÚBLICOS ============

@app.get("/")
def root():
    return {
        "message": "JWT Practice API",
        "endpoints": {
            "public": ["/", "/health", "/token", "/token/refresh"],
            "protected": ["/me", "/socios", "/socios/{id}", "/admin/users"]
        },
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}


@app.post("/token", response_model=Token)
def login(form_data: LoginRequest):
    """
    Login con username/password. Devuelve access_token y refresh_token.
    
    Usuarios de prueba:
    - profesor1 / Pass1234! (role: teacher)
    - admin1 / Admin5678! (role: admin)  
    - root / Root9999! (role: root)
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, expire_time = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(user["username"])
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@app.post("/token/refresh", response_model=Token)
def refresh_token(refresh_token: str = Header(..., alias="X-Refresh-Token")):
    """
    Obtener nuevo access_token usando refresh_token.
    Header requerido: X-Refresh-Token: <token>
    """
    username = verify_refresh_token(refresh_token)
    user = get_user(username)
    
    if not user or user.get("disabled"):
        raise HTTPException(status_code=400, detail="Usuario inválido o deshabilitado")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, _ = create_access_token(
        data={"sub": username, "role": user["role"]},
        expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(username)
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


# ============ DEPENDENCIAS DE AUTENTICACIÓN ============

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    username = payload.get("sub")
    user = get_user(username)
    
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.get("disabled"):
        raise HTTPException(status_code=400, detail="Usuario deshabilitado")
    
    return {**user, "token_payload": payload}


def require_role(allowed_roles: List[str]):
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol: {allowed_roles}"
            )
        return current_user
    return role_checker


# ============ ENDPOINTS PROTEGIDOS ============

@app.get("/me", response_model=dict)
def read_users_me(current_user: dict = Depends(get_current_user)):
    """Obtener información del usuario autenticado"""
    return {
        "username": current_user["username"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "token_data": current_user["token_payload"]
    }


@app.get("/socios", response_model=List[SocioResponse])
def list_socios(
    skip: int = 0, 
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Listar socios (cualquier usuario autenticado)"""
    result = socios_db[skip : skip + limit]
    return result


@app.post("/socios", response_model=SocioResponse, status_code=201)
def create_socio(
    socio: SocioCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear nuevo socio (requiere autenticación)"""
    global socio_id_counter
    
    # Verificar DNI único
    for s in socios_db:
        if s["dni"] == socio.dni:
            raise HTTPException(status_code=400, detail="DNI ya existe")
    
    new_socio = {
        "id": socio_id_counter,
        "nombre": socio.nombre,
        "email": socio.email,
        "dni": socio.dni,
        "created_by": current_user["username"],
        "created_at": datetime.now()
    }
    socios_db.append(new_socio)
    socio_id_counter += 1
    
    return new_socio


@app.get("/socios/{socio_id}", response_model=SocioResponse)
def get_socio(
    socio_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Obtener socio por ID"""
    for socio in socios_db:
        if socio["id"] == socio_id:
            return socio
    raise HTTPException(status_code=404, detail="Socio no encontrado")


@app.delete("/socios/{socio_id}")
def delete_socio(
    socio_id: int,
    current_user: dict = Depends(require_role(["admin", "root"]))
):
    """Eliminar socio (solo admin/root)"""
    global socios_db
    for i, socio in enumerate(socios_db):
        if socio["id"] == socio_id:
            del socios_db[i]
            return {"message": f"Socio {socio_id} eliminado"}
    raise HTTPException(status_code=404, detail="Socio no encontrado")


@app.get("/admin/users", response_model=List[dict])
def list_all_users(
    current_user: dict = Depends(require_role(["root"]))
):
    """Listar todos los usuarios del sistema (solo root)"""
    return [
        {"username": u["username"], "full_name": u["full_name"], "role": u["role"]}
        for u in fake_users_db.values()
    ]


# ============ ENDPOINTS DE DEBUG/PRÁCTICA ============

@app.get("/debug/token-info")
def debug_token(current_user: dict = Depends(get_current_user)):
    """Ver información cruda del token (para aprendizaje)"""
    import base64
    
    token = current_user["token_payload"]
    # Recrear header y payload del token original
    header_b64 = base64.urlsafe_b64encode(
        f'{{"alg":"HS256","typ":"JWT"}}'.encode()
    ).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(
        str(token).replace("'", '"').encode()
    ).decode().rstrip("=")
    
    return {
        "decoded_payload": token,
        "expires_at": datetime.fromtimestamp(token["exp"]).isoformat(),
        "issued_at": datetime.fromtimestamp(token["iat"]).isoformat(),
        "time_remaining_seconds": token["exp"] - time.time(),
        "note": "En producción, nunca expongas la SECRET_KEY"
    }


@app.post("/admin/seed-socios")
def seed_data(count: int = 5, current_user: dict = Depends(require_role(["admin", "root"]))):
    """Generar socios de prueba automáticamente"""
    global socio_id_counter
    import random
    
    nombres = ["María", "Juan", "Laura", "Pedro", "Sofía", "Miguel", "Carmen", "José"]
    apellidos = ["López", "García", "Martínez", "Rodríguez", "Fernández", "Pérez"]
    
    created = []
    for i in range(count):
        nombre = f"{random.choice(nombres)} {random.choice(apellidos)}"
        dni_num = random.randint(10000000, 99999999)
        letra = "TRWAGMYFPDXBNJZSQVHLCKE"[dni_num % 23]
        
        socio = {
            "id": socio_id_counter,
            "nombre": nombre,
            "email": f"socio{socio_id_counter}@ejemplo.com",
            "dni": f"{dni_num}{letra}",
            "created_by": current_user["username"],
            "created_at": datetime.now()
        }
        socios_db.append(socio)
        created.append(socio)
        socio_id_counter += 1
    
    return {"created": len(created), "socios": created}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
