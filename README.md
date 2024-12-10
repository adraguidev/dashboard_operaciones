# Sistema de Gestión de Expedientes Migratorios

## 📋 Descripción
Sistema para la gestión, seguimiento y análisis de expedientes migratorios, incluyendo módulos para Calidad Migratoria (CCM), Prórroga de Residencia (PRR), Calidad Migratoria Especial (CCM-ESP) y Solicitudes (SOL).

## 🚀 Características Principales
- Descarga y consolidación automática de datos
- Gestión de reportes evaluados
- Análisis predictivo de ingresos
- Rankings de expedientes trabajados
- Seguimiento de expedientes pendientes
- Integración con MongoDB para almacenamiento
- Interfaz web interactiva con Streamlit
- Soporte para múltiples módulos migratorios

## 🛠️ Requisitos
- Python 3.8+
- MongoDB
- Cuenta de Google (para funcionalidades de Google Sheets)

## 📦 Instalación

1. Clonar el repositorio:
bash
git clone [url-del-repositorio]
cd [nombre-del-directorio]

2. Crear y activar entorno virtual:
bash
python -m venv venv
source venv/bin/activate # Linux/Mac
venv\Scripts\activate # Windows

3. Instalar dependencias:
bash
pip install -r requirements.txt

4. Configurar variables de entorno:
Crear archivo `.env` con:
MONGODB_URI=tu_uri_de_mongodb
MONGODB_PASSWORD=tu_password

## 🔧 Configuración

### MongoDB
1. Configurar índices necesarios:
bash
python scripts/setup_mongodb.py

### Google Sheets (para módulo SPE)
1. Configurar credenciales de Google en `.credentials/`
2. Verificar permisos y scopes necesarios

## 🚀 Uso

### Iniciar la aplicación
bash
streamlit run dashboard.py

### Funcionalidades principales:
1. **Descarga y Consolidación**
   ```bash
   python main.py
   ```
   Seleccionar opción 1 del menú

2. **Gestión de Reportes**
   ```bash
   python manejo_reportes.py
   ```

3. **Subir datos a MongoDB**
   ```bash
   python main.py
   ```
   Seleccionar opción 7 del menú

## 📁 Estructura del Proyecto
├── config/ # Configuraciones
├── descargas/ # Archivos descargados
├── modules/ # Módulos del sistema
├── scripts/ # Scripts de utilidad
├── src/ # Código fuente principal
├── tabs/ # Componentes de interfaz
├── requirements.txt # Dependencias
└── README.md # Este archivo


## 🔍 Módulos Disponibles
- CCM (Calidad Migratoria)
- PRR (Prórroga de Residencia)
- CCM-ESP (Calidad Migratoria Especial)
- CCM-LEY (Calidad Migratoria Ley)
- SOL (Solicitudes)
- SPE (Sistema de Permisos Especiales)

## 🤝 Contribución
1. Fork del repositorio
2. Crear rama para feature: `git checkout -b feature/NuevaCaracteristica`
3. Commit cambios: `git commit -m 'Agregar nueva característica'`
4. Push a la rama: `git push origin feature/NuevaCaracteristica`
5. Crear Pull Request

## 📝 Notas Importantes
- Asegurar permisos correctos para acceso a MongoDB
- Mantener actualizadas las credenciales de Google
- Verificar la configuración de red para acceso a servicios

## 🔒 Seguridad
- No compartir credenciales en el código
- Usar variables de entorno para datos sensibles
- Mantener actualizadas las dependencias

## 📫 Soporte
Para reportar problemas o solicitar ayuda, crear un issue en el repositorio.