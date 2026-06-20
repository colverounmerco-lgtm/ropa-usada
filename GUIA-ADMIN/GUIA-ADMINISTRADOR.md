# Guía del Administrador — Marketplace de Ropa Usada

---

## 1. ACCESO AL PANEL DE ADMINISTRACIÓN

### URL de la aplicación
```
https://web-production-1f288d.up.railway.app
```

### Credenciales de administrador
- **Email:** sm9676968@gmail.com
- **Contraseña:** colombiaecuador

> ⚠️ IMPORTANTE: Cambia la contraseña en Railway (ver sección 7) cuando puedas.

### Cómo entrar
1. Ve a la URL de la aplicación
2. Clic en "Iniciar sesión" (arriba a la derecha)
3. Ingresa el email y contraseña de admin
4. Serás redirigido automáticamente al panel de administración

### URL directa al panel admin
```
https://web-production-1f288d.up.railway.app/admin
```

---

## 2. PANEL DE ADMINISTRACIÓN — RESUMEN

Desde el panel admin puedes gestionar:

| Sección | URL | Para qué sirve |
|---|---|---|
| Dashboard | /admin | Resumen general con estadísticas |
| Recargas Wallet | /admin/recargas | Aprobar/rechazar depósitos de vendedores |
| Retiros | /admin/retiros | Aprobar/rechazar solicitudes de retiro |
| Mensajes | /admin/mensajes | Responder chats de usuarios |
| Usuarios | /admin/usuarios | Ver y activar/desactivar cuentas |
| Prendas | /admin/prendas | Ver y eliminar prendas del catálogo |

---

## 3. CÓMO COBRAR TU COMISIÓN DEL 7%

### ¿Cómo funciona?
- Cada vendedor debe tener saldo en su **wallet** para publicar prendas
- Cuando marca una prenda como vendida, se descuenta automáticamente el **7% del precio** de su wallet
- Ese 7% queda reflejado en los **movimientos de wallet** de cada vendedor
- Tú recibes ese dinero cuando el vendedor **recarga su wallet** (ya fue depositado en tu cuenta bancaria)

### Flujo de dinero
```
Vendedor hace transferencia a tu cuenta bancaria
→ Sube comprobante en la app
→ TÚ apruebas la recarga
→ El saldo entra al wallet del vendedor
→ Cada venta descuenta el 7% del wallet
→ Si pide retiro, tú le devuelves lo que queda
```

### ¿Cuánto te corresponde?
Lo que cobras = Total de recargas aprobadas - Total de retiros aprobados

---

## 4. GESTIONAR RECARGAS DE WALLET

Cuando un vendedor hace una transferencia y sube el comprobante:

1. Ve a **Panel Admin → Recargas Wallet** (o entra a `/admin/recargas`)
2. Verás las solicitudes **pendientes** marcadas en amarillo
3. Descarga o abre el comprobante (clic en el link)
4. Verifica en tu cuenta bancaria que el dinero llegó
5. Si llegó → clic en **✅ Aprobar** (el saldo se acredita automáticamente al vendedor)
6. Si no llegó o es falso → clic en **❌ Rechazar**

> 📋 El número de recargas pendientes aparece como alerta en el dashboard.

---

## 5. GESTIONAR SOLICITUDES DE RETIRO

Cuando un vendedor quiere retirar su saldo:

1. Ve a **Panel Admin → Retiros** (o entra a `/admin/retiros`)
2. Verás los datos bancarios del vendedor y el monto
3. Haz la transferencia bancaria al vendedor por fuera
4. Una vez transferido → clic en **✅ Aprobar**
   - El sistema descuenta el monto del wallet automáticamente
5. Si no puedes procesar el retiro → clic en **❌ Rechazar**

> ⚠️ Solo aprueba DESPUÉS de haber transferido el dinero.

---

## 6. GESTIONAR MENSAJES (CHAT)

Cuando un usuario te escribe:

1. Aparecerá un **número rojo** en el botón 💬 flotante
2. Ve a **Panel Admin → Mensajes** (o entra a `/admin/mensajes`)
3. Verás la lista de conversaciones con los no leídos marcados
4. Clic en **Ver** para abrir la conversación
5. Escribe tu respuesta y clic en **Enviar**

El chat se actualiza automáticamente cada 15 segundos.

---

## 7. GESTIONAR USUARIOS

Desde `/admin/usuarios` puedes:
- Ver todos los compradores y vendedores registrados
- **Desactivar** una cuenta si hay problemas (el usuario no podrá iniciar sesión)
- **Reactivar** cuentas desactivadas

---

## 8. GESTIONAR PRENDAS

Desde `/admin/prendas` puedes:
- Ver todas las prendas publicadas en el marketplace
- Eliminar prendas que incumplan las normas

---

## 9. CAMBIAR CONFIGURACIÓN EN RAILWAY

Para cambiar cualquier configuración (nombre de tienda, banco, contraseña admin, etc.):

1. Ve a **https://railway.app** e inicia sesión
2. Entra al proyecto **capable-beauty**
3. Clic en la tarjeta **web**
4. Pestaña **Variables**
5. Busca la variable que quieres cambiar, clic en los 3 puntos `⋮` → Edit
6. Cambia el valor y guarda
7. Railway redespliega automáticamente

### Variables importantes
| Variable | Para qué sirve |
|---|---|
| `ADMIN_EMAIL` | Email para entrar al panel admin |
| `ADMIN_PASSWORD` | Contraseña del admin |
| `NOMBRE_TIENDA` | Nombre que aparece en toda la app |
| `BANCO_NOMBRE` | Tu banco (lo ven los vendedores al recargar) |
| `BANCO_CUENTA` | Tu número de cuenta bancaria |
| `BANCO_TITULAR` | Tu nombre como titular |

---

## 10. CÓMO ACTUALIZAR LA APP (hacer cambios)

Si haces cambios al código con Claude Code:

1. En la terminal (cmd), en la carpeta `ropa-usada`:
```
git add .
git commit -m "descripcion del cambio"
git push
```
2. Railway detecta el push y redespliega automáticamente (1-2 minutos)

---

## 11. SERVICIOS USADOS (y dónde administrarlos)

| Servicio | Para qué | Acceso |
|---|---|---|
| **Railway** | Servidor + base de datos | railway.app |
| **Cloudinary** | Almacenamiento de imágenes | cloudinary.com |
| **GitHub** | Código fuente | github.com/colverounmerco-lgtm/ropa-usada |

### Cloudinary (imágenes)
- Las fotos de prendas y comprobantes se guardan aquí
- Dashboard: console.cloudinary.com
- Cloud name: `dx38sujqd`

### Railway (servidor)
- La app vive aquí 24/7
- Plan actual: **Trial** (30 días gratis / $5.00)
- Cuando se acabe el trial, necesitarás agregar una tarjeta de pago

---

## 12. SOLUCIÓN DE PROBLEMAS COMUNES

| Problema | Causa | Solución |
|---|---|---|
| La app no carga | El servidor crasheó | Ve a Railway → web → Restart |
| Un vendedor no puede publicar | Wallet en $0 | Pídele que recargue |
| Un usuario no puede entrar | Cuenta desactivada | Ve a Usuarios y actívala |
| La app va lenta | Plan trial con recursos limitados | Considera el plan de pago en Railway |

---

## 13. DATOS IMPORTANTES

- **Base de datos:** PostgreSQL en Railway (se respalda automáticamente)
- **Imágenes:** Cloudinary (plan gratuito: 25GB de almacenamiento)
- **Comisión:** 7% por cada venta, descontada automáticamente del wallet del vendedor
- **Wallet mínimo para vender:** $1.00

---

*Generado por Claude Code — Actualizado junio 2026*
