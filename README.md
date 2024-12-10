# Sistema de Gestión de Expedientes Migratorios

## 📋 Descripción
Sistema integral para la gestión, seguimiento y análisis de expedientes migratorios, incluyendo módulos para Calidad Migratoria (CCM), Prórroga de Residencia (PRR), Calidad Migratoria Especial (CCM-ESP) y Solicitudes (SOL).

## 🚀 Características Principales
- Descarga y consolidación automática de datos
- Dashboard interactivo con múltiples reportes
- Sistema de rankings y seguimiento de expedientes
- Gestión de asignaciones a evaluadores
- Análisis predictivo y estadístico
- Integración con MongoDB para almacenamiento persistente
- Soporte para Google Sheets

## 🛠️ Tecnologías Utilizadas
- Python 3.x
- Streamlit >= 1.28.0
- MongoDB (pymongo >= 4.0.0)
- Pandas >= 2.0.0
- NumPy >= 1.24.0
- Plotly >= 4.14.3
- Google API (google-auth >= 1.35.0)
- Prophet >= 1.0 (para análisis predictivo)

## 📦 Requisitos Previos
- Python 3.x instalado
- MongoDB instalado y configurado
- Credenciales de Google API configuradas
- Variables de entorno configuradas

## 🗂️ Estructura del Proyecto
├── config/ # Configuraciones y constantes
├── descargas/ # Carpeta para archivos descargados
├── modules/ # Módulos específicos (CCM, PRR, etc.)
├── src/ # Código fuente principal
│ ├── utils/ # Utilidades y helpers
│ └── tabs/ # Componentes de la interfaz
├── scripts/ # Scripts de utilidad
├── .env # Variables de entorno
├── requirements.txt # Dependencias del proyecto
└── README.md # Documentación

## 🚀 Uso

1. Iniciar la aplicación:
bash
streamlit run dashboard.py

2. Acceder a través del navegador:
http://localhost:8501


## 📊 Módulos Principales

### Dashboard
- Visualización de estadísticas en tiempo real
- Filtros dinámicos por fecha y tipo de expediente
- Exportación de reportes en Excel

### Gestión de Expedientes
- Seguimiento de estado de expedientes
- Asignación a evaluadores
- Control de plazos

### Reportes
- Rankings de productividad
- Análisis de tiempos de procesamiento
- Estadísticas por evaluador

## 🔒 Seguridad
- Autenticación mediante MongoDB
- Encriptación de datos sensibles
- Control de acceso por roles

## 🤝 Contribución
1. Fork del repositorio
2. Crear rama para nueva funcionalidad
3. Commit de cambios
4. Push a la rama
5. Crear Pull Request

## 📝 Notas Importantes
- Mantener actualizadas las credenciales
- Realizar backups periódicos de la base de datos
- Revisar logs regularmente
- Asegurar que todas las dependencias estén instaladas según requirements.txt

## 📄 Licencia
Derechos Reservados - Uso Interno

## 👥 Contacto
Para soporte técnico o consultas, contactar al equipo de desarrollo.

---

**Nota**: Este sistema está diseñado para uso interno y requiere las credenciales y permisos apropiados para su funcionamiento.

