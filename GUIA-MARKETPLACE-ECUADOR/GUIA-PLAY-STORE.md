# Guía para Publicar en Google Play Store

---

## RESUMEN

Tu app ya está lista como PWA (Progressive Web App). Para publicarla en Play Store
necesitas seguir 4 pasos:

1. Generar el APK con PWABuilder (gratis)
2. Vincular el dominio con el APK (2 variables en Railway)
3. Crear cuenta Google Play Developer ($25 una sola vez)
4. Subir la app y esperar revisión (1–3 días)

---

## PASO 1 — Generar el APK de Android (gratis, 5 minutos)

1. Espera que Railway haga el deploy después de cualquier cambio (~2 min)
2. Abre el navegador y ve a:
   ```
   https://www.pwabuilder.com
   ```
3. En el cuadro de texto escribe la URL de tu app en Railway:
   ```
   https://web-production-1f288d.up.railway.app
   ```
4. Clic en **"Start"** — PWABuilder analiza la app automáticamente
5. Cuando termine el análisis, clic en **"Package for stores"**
6. Selecciona **"Google Play"**
7. Completa el formulario:
   - **Package ID:** elige un nombre único en formato `com.tunombre.marketplace`
     Ejemplo: `com.mimarketplace.ecuador`
     (Este nombre NO se puede cambiar después de publicar)
   - **App name:** el nombre de tu marketplace
   - **Version:** 1.0.0
   - Deja el resto con los valores por defecto
8. Clic en **"Generate"** y descarga el ZIP

### ¿Qué contiene el ZIP?
- `app-release-unsigned.apk` — el archivo para subir a Play Store
- `app-release.aab` — formato alternativo (preferido por Google)
- `signing-key.jks` — clave de firma (GUÁRDALA, la necesitas para actualizaciones)
- `signing-key-info.txt` — contiene el **SHA256 fingerprint** (lo necesitas en el Paso 2)

> ⚠️ IMPORTANTE: Guarda el archivo `signing-key.jks` en un lugar seguro.
> Si lo pierdes, no podrás actualizar la app en Play Store.

---

## PASO 2 — Vincular el dominio con el APK (Railway)

Esto es necesario para que Android confíe en tu app y funcione correctamente.

1. Ve a Railway: https://railway.app
2. Abre tu proyecto → pestaña **Variables**
3. Añade estas dos variables:

   | Variable | Valor |
   |---|---|
   | `TWA_PACKAGE` | El Package ID que elegiste (ej: `com.mimarketplace.ecuador`) |
   | `TWA_FINGERPRINT` | El SHA256 que está en `signing-key-info.txt` del ZIP |

   El fingerprint tiene este formato:
   ```
   AA:BB:CC:DD:EE:FF:...  (32 pares separados por :)
   ```

4. Clic en **"Deploy"** para aplicar los cambios
5. Espera que Railway termine el deploy (~2 min)

---

## PASO 3 — Crear cuenta Google Play Developer

Solo se hace una vez y sirve para publicar todas tus apps.

1. Ve a: https://play.google.com/console
2. Inicia sesión con tu cuenta de Google
3. Clic en **"Comenzar"**
4. Paga el registro: **$25 USD** (tarjeta de crédito/débito)
5. Completa el perfil de desarrollador:
   - Nombre del desarrollador (el que verán los usuarios en Play Store)
   - Correo de contacto
   - Teléfono

---

## PASO 4 — Subir la app a Play Store

### Crear la app
1. En Google Play Console, clic en **"Crear app"**
2. Completa:
   - **Nombre de la app:** nombre de tu marketplace
   - **Idioma predeterminado:** Español (Ecuador)
   - **Tipo de app:** App (no juego)
   - **Gratuita o de pago:** Gratuita
3. Clic en **"Crear app"**

### Configurar la ficha de Play Store
Ve a **Presencia en Play Store → Ficha principal de Play Store**

- **Título:** nombre de tu app (máx. 30 caracteres)
- **Descripción breve:** máx. 80 caracteres
  Ejemplo: *"Compra, vende y ofrece servicios en Ecuador"*
- **Descripción completa:** máx. 4000 caracteres
  Explica qué es la app, qué pueden hacer los usuarios, cómo funciona el marketplace
- **Capturas de pantalla:** mínimo 2 fotos de la app en el celular (usa el navegador con F12 para simular móvil y tomar capturas)
- **Ícono:** sube la imagen del ícono (512x512 PNG) — la genera PWABuilder en el ZIP
- **Gráfico de presentación:** opcional (1024x500 PNG)

### Clasificación de contenido
Ve a **Política → Clasificación de contenido**
- Completa el cuestionario (es una tienda, sin violencia ni adultos)
- Obtendrás clasificación **"Para todos"**

### Público objetivo
- Edad mínima: 13 años
- No está dirigida a niños

### País de distribución
Ve a **Distribución de la app**
- Puedes seleccionar solo **Ecuador** o todos los países
- Para limitar a Ecuador: desactiva "Disponible en todos los países" y busca Ecuador

### Subir el APK/AAB
Ve a **Producción → Versiones**
1. Clic en **"Crear nueva versión"**
2. Sube el archivo `.aab` (o `.apk`) del ZIP de PWABuilder
3. En "Notas de la versión" escribe: *"Primera versión del marketplace"*
4. Clic en **"Guardar"** → **"Revisar versión"** → **"Comenzar lanzamiento"**

### Enviar para revisión
- Google revisa la app en **1 a 3 días hábiles**
- Te llega un email cuando está aprobada
- Si rechazan algo, te explican qué corregir

---

## ACTUALIZAR LA APP EN PLAY STORE

Cada vez que hagas cambios en el código y quieras que la app en Play Store se actualice:

1. Los cambios en Railway se despliegan automáticamente (los usuarios siempre ven la versión más reciente sin actualizar Play Store)
2. Si cambias algo fundamental (nombre del paquete, íconos, etc.), debes subir una nueva versión a Play Store:
   - Vuelve a PWABuilder con la misma URL
   - Usa el mismo Package ID y el mismo archivo `signing-key.jks`
   - Genera un nuevo APK/AAB
   - Sube en Play Console → Producción → Nueva versión

> La ventaja de una PWA es que el contenido de la app se actualiza automáticamente
> con cada deploy en Railway. Solo necesitas subir una nueva versión a Play Store
> cuando cambia la estructura de la app (no el contenido).

---

## ÍCONOS PERSONALIZADOS

Los íconos actuales son una "M" azul marino sobre fondo azul. Para usar tu propio logo:

1. Prepara una imagen PNG cuadrada de al menos **512x512 píxeles**
2. Reemplaza los archivos en la carpeta `static/icons/` del proyecto
3. Haz commit y push (Railway actualiza automáticamente)
4. Vuelve a generar el APK en PWABuilder para que el nuevo ícono quede en Play Store

---

## PREGUNTAS FRECUENTES

**¿Cuánto cuesta publicar?**
Solo $25 USD una vez para la cuenta de desarrollador. PWABuilder es gratis.

**¿Cuánto tarda en aparecer en Play Store?**
Entre 1 y 3 días hábiles para la primera publicación.

**¿Los usuarios de Ecuador pueden descargarla?**
Sí, si configuras Ecuador como país de distribución. También puedes abrirla a todos los países.

**¿Necesito actualizar Play Store cada vez que cambio la app?**
No. Los cambios en Railway (código, textos, precios) se ven inmediatamente sin actualizar Play Store. Solo subes una nueva versión si cambias íconos, nombre de la app o el manifiesto.

**¿Funciona también en iPhone (App Store)?**
PWABuilder también genera paquetes para App Store (requiere una Mac para compilar y $99/año de Apple Developer). Se puede hacer después.

**¿Puedo instalarla sin Play Store?**
Sí. Cualquier usuario con Chrome en Android puede ir a la URL y tocar "Añadir a pantalla de inicio" — funciona como app sin necesitar Play Store.

---

## CONTACTO Y SOPORTE

- **URL de la app:** https://web-production-1f288d.up.railway.app
- **Repositorio:** github.com/colverounmerco-lgtm/ropa-usada
- **Railway:** railway.app (panel de control del servidor)
- **PWABuilder:** pwabuilder.com (generador de APK)
- **Play Console:** play.google.com/console
