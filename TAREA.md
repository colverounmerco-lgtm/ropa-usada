# App de Venta de Ropa Usada

## Cómo instalar y correr

### 1. Instalar Python
Si no tienes Python: https://www.python.org/downloads/
Marca la casilla "Add Python to PATH" al instalar.

### 2. Crear el archivo .env
Duplica `.env.example` y renómbralo `.env`. Llena los valores:
```
SECRET_KEY=cualquier-texto-largo-y-aleatorio
ADMIN_PASSWORD=tu-contraseña-segura
WHATSAPP_NUMERO=593XXXXXXXXX  ← tu número con código de país, sin + ni espacios
NOMBRE_TIENDA=Mi Tienda de Ropa
```

### 3. Instalar dependencias
Abre la terminal en la carpeta del proyecto y ejecuta:
```
pip install -r requirements.txt
```

### 4. Correr la app
```
python main.py
```

### 5. Abrir en el navegador
- Tienda pública:  http://localhost:5000
- Panel de admin:  http://localhost:5000/admin

---

## Qué hace la app

- **Catálogo público** con filtros por categoría, talla y precio
- **Página de cada prenda** con fotos y botón de WhatsApp para consultar
- **Panel de admin** con login para:
  - Agregar prendas con fotos
  - Editar información
  - Marcar como vendidas / disponibles
  - Eliminar prendas
  - Ver estadísticas (total, disponibles, vendidas)

## Estructura de archivos
```
ropa-usada/
├── main.py          ← App principal
├── models.py        ← Base de datos
├── config.py        ← Configuración
├── .env             ← Tus credenciales (no compartir)
├── requirements.txt ← Dependencias
├── templates/       ← Páginas HTML
└── static/          ← CSS, JS e imágenes subidas
```
