import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from config.settings import MONGODB_CONFIG

def render_ranking_report_tab(data, selected_module, collection):
    st.header("Ranking de Expedientes Trabajados")

    try:
        # Verificar si hay datos del módulo
        if data is None:
            st.warning(f"No se encontraron datos para el módulo {selected_module}.")
            return

        # Obtener última fecha registrada
        ultima_fecha_db = get_last_date_from_db(selected_module, collection)
        
        if ultima_fecha_db:
            # Agregar opción para resetear último día
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"Última fecha registrada: {ultima_fecha_db.strftime('%d/%m/%Y')}")
            with col2:
                if st.button("Resetear último día"):
                    # Eliminar registros del último día
                    collection.delete_many({
                        "modulo": selected_module,
                        "fecha": ultima_fecha_db
                    })
                    st.success("Último día eliminado. Los datos se actualizarán al recargar.")
                    st.rerun()

        # Resto del código original...
        fecha_actual = datetime.now().date()
        fecha_ayer = fecha_actual - pd.Timedelta(days=1)
        fecha_inicio_excel = fecha_actual - pd.Timedelta(days=7)

        # Convertir y filtrar datos por fechas relevantes
        data['FECHA DE TRABAJO'] = pd.to_datetime(data['FECHA DE TRABAJO'], errors='coerce')
        datos_nuevos = data[
            (data['FECHA DE TRABAJO'].dt.date >= fecha_inicio_excel) &
            (data['FECHA DE TRABAJO'].dt.date <= fecha_ayer)
        ]

        # Obtener última fecha registrada en la base de datos
        ultima_fecha_db = get_last_date_from_db(selected_module, collection)
        if ultima_fecha_db:
            datos_a_guardar = datos_nuevos[
                datos_nuevos['FECHA DE TRABAJO'].dt.date > ultima_fecha_db.date()
            ]
        else:
            datos_a_guardar = datos_nuevos

        # Guardar nuevos registros si existen
        if not datos_a_guardar.empty:
            nuevos_registros = []
            for fecha, grupo in datos_a_guardar.groupby(datos_a_guardar['FECHA DE TRABAJO'].dt.date):
                ranking_dia = grupo.groupby('EVALASIGN').size().reset_index(name='cantidad')
                ranking_dia.columns = ['evaluador', 'cantidad']
                nuevos_registros.append({
                    "fecha": pd.Timestamp(fecha),
                    "datos": ranking_dia.to_dict('records'),
                    "modulo": selected_module
                })
            
            if nuevos_registros:
                collection.insert_many(nuevos_registros)

        # Mostrar registros históricos
        registros_historicos = list(collection.find({"modulo": selected_module}).sort("fecha", -1))
        if registros_historicos:
            df_historico = pd.DataFrame()
            
            for registro in registros_historicos:
                fecha = pd.Timestamp(registro['fecha']).strftime('%d/%m')
                if pd.Timestamp(registro['fecha']).date() < fecha_actual:
                    df_temp = pd.DataFrame(registro['datos'])
                    if not df_temp.empty:
                        df_pivot = pd.DataFrame({
                            'EVALASIGN': df_temp['evaluador'].tolist(),
                            fecha: df_temp['cantidad'].tolist()
                        })
                        if df_historico.empty:
                            df_historico = df_pivot
                        else:
                            df_historico = df_historico.merge(
                                df_pivot, on='EVALASIGN', how='outer'
                            )

            if not df_historico.empty:
                # Reemplazar NaN con ceros y convertir valores a enteros
                df_historico = df_historico.fillna(0)
                df_historico.iloc[:, 1:] = df_historico.iloc[:, 1:].astype(int)

                # Ordenar y agregar día de la semana a las fechas
                dias_semana = {
                    0: 'Lun',
                    1: 'Mar',
                    2: 'Mie',
                    3: 'Jue',
                    4: 'Vie',
                    5: 'Sab',
                    6: 'Dom'
                }

                fecha_cols = [col for col in df_historico.columns if col != 'EVALASIGN']
                nuevas_cols = []
                for col in fecha_cols:
                    if col not in ['Total', 'Promedio']:
                        fecha = pd.to_datetime(col + f"/{datetime.now().year}", format='%d/%m/%Y')
                        dia_semana = dias_semana[fecha.weekday()]
                        nueva_col = f"{dia_semana} {col}"
                        df_historico = df_historico.rename(columns={col: nueva_col})
                        nuevas_cols.append(nueva_col)
                    else:
                        nuevas_cols.append(col)

                # Ordenar fechas de más antiguo a más reciente
                df_historico = df_historico.reindex(
                    columns=['EVALASIGN'] + sorted(
                        [col for col in nuevas_cols if col not in ['Total', 'Promedio']],
                        key=lambda x: pd.to_datetime(x.split(' ')[-1] + f"/{datetime.now().year}", format='%d/%m/%Y')
                    ) + ['Total', 'Promedio']
                )

                # Calcular el promedio especial
                def calcular_promedio_especial(row):
                    fechas_columnas = [col for col in row.index if col != 'EVALASIGN' and col not in ['Total', 'Promedio']]
                    dias_trabajo = []
                    
                    for fecha_col in fechas_columnas:
                        # Extraer solo la parte de la fecha (dd/mm) del nombre de la columna
                        fecha_str = fecha_col.split(' ')[-1]  # Obtener "dd/mm" de "Día dd/mm"
                        fecha_completa = pd.to_datetime(fecha_str + f"/{datetime.now().year}", format='%d/%m/%Y')
                        dia_semana = fecha_completa.weekday()  # 0 = Lunes, 6 = Domingo
                        cantidad = row[fecha_col]
                        
                        if cantidad > 0:
                            dias_trabajo.append((fecha_str, dia_semana, cantidad))
                    
                    # Contar días laborables (L-V) con trabajo
                    dias_laborables = sum(1 for _, dia, _ in dias_trabajo if dia < 5)
                    
                    # Sumar todas las cantidades
                    total_trabajo = sum(cantidad for _, _, cantidad in dias_trabajo)
                    
                    # Si no hay días laborables pero hay trabajo en fin de semana,
                    # consideramos que es trabajo recuperado
                    if dias_laborables == 0 and dias_trabajo:
                        return total_trabajo / 5
                    
                    # Si hay días laborables, dividimos entre 5 (semana completa)
                    if dias_laborables > 0:
                        return total_trabajo / 5
                    
                    return 0

                # Aplicar el cálculo del promedio a cada fila
                df_historico['Promedio'] = df_historico.apply(calcular_promedio_especial, axis=1)

                # Agregar columna 'Total' y ordenar
                df_historico['Total'] = df_historico.iloc[:, 1:-1].sum(axis=1)  # Excluir 'Promedio' del total
                df_historico = df_historico.sort_values(by='Total', ascending=False)

                # Restablecer el índice, comenzando desde 1
                df_historico.reset_index(drop=True, inplace=True)
                df_historico.index += 1

                # Convertir todas las columnas numéricas a enteros antes de mostrar
                columnas_numericas = [col for col in df_historico.columns if col not in ['EVALASIGN', 'Promedio']]
                for col in columnas_numericas:
                    df_historico[col] = df_historico[col].astype(int)

                # Mostrar tabla con formato especial para el promedio
                st.subheader(f"Ranking de Expedientes Trabajados - {selected_module} (Últimos 15 días hasta ayer)")
                st.table(
                    df_historico.style.format({
                        'Promedio': "{:.1f}"  # Solo formato especial para el promedio
                    })
                )

                # Botón para descargar ranking como Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_historico.to_excel(writer, index=False, sheet_name='Ranking_Historico')
                output.seek(0)
                
                st.download_button(
                    label="Descargar Ranking Histórico",
                    data=output,
                    file_name=f"Ranking_Historico_{selected_module}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                # Nueva sección para inconsistencias de fechas
                st.subheader("Inconsistencias en Fechas de Trabajo")
                
                # Filtrar datos de los últimos 30 días
                fecha_30_dias = pd.Timestamp.now() - pd.Timedelta(days=30)
                datos_recientes = data[data['FechaPre'] >= fecha_30_dias].copy()
                
                # Convertir fechas si no lo están
                datos_recientes['FECHA DE TRABAJO'] = pd.to_datetime(datos_recientes['FECHA DE TRABAJO'], errors='coerce')
                datos_recientes['FechaPre'] = pd.to_datetime(datos_recientes['FechaPre'], errors='coerce')
                
                # Filtrar primero los registros que tienen ambas fechas (no nulos)
                datos_validos = datos_recientes.dropna(subset=['FECHA DE TRABAJO', 'FechaPre'])
                
                # Calcular la diferencia en días entre las fechas
                datos_validos['DiferenciaDias'] = abs((datos_validos['FECHA DE TRABAJO'] - datos_validos['FechaPre']).dt.days)
                
                # Encontrar inconsistencias (diferencia mayor a 2 días)
                inconsistencias = datos_validos[
                    datos_validos['DiferenciaDias'] > 2
                ][['NumeroTramite', 'EVALASIGN', 'FECHA DE TRABAJO', 'FechaPre', 'DiferenciaDias', 'ESTADO', 'DESCRIPCION']].copy()
                
                if not inconsistencias.empty:
                    # Formatear fechas para visualización
                    inconsistencias['FECHA DE TRABAJO'] = inconsistencias['FECHA DE TRABAJO'].dt.strftime('%d/%m/%Y')
                    inconsistencias['FechaPre'] = inconsistencias['FechaPre'].dt.strftime('%d/%m/%Y')
                    
                    # Renombrar columnas para mejor visualización
                    inconsistencias.columns = [
                        'N° Expediente',
                        'Evaluador',
                        'Fecha de Trabajo',
                        'Fecha Pre',
                        'Diferencia en Días',
                        'Estado',
                        'Descripción'
                    ]
                    
                    # Ordenar por diferencia de días (mayor a menor)
                    inconsistencias = inconsistencias.sort_values('Diferencia en Días', ascending=False)
                    
                    # Mostrar tabla de inconsistencias con ancho personalizado
                    st.dataframe(
                        inconsistencias,
                        use_container_width=True,  # Usar todo el ancho disponible
                        height=400  # Altura fija para mejor visualización
                    )
                    
                    # Botón para descargar inconsistencias
                    output_inconsistencias = BytesIO()
                    with pd.ExcelWriter(output_inconsistencias, engine='openpyxl') as writer:
                        inconsistencias.to_excel(writer, index=False, sheet_name='Inconsistencias_Fechas')
                    output_inconsistencias.seek(0)
                    
                    st.download_button(
                        label="Descargar Reporte de Inconsistencias",
                        data=output_inconsistencias,
                        file_name=f"Inconsistencias_Fechas_{selected_module}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    # Mostrar resumen
                    st.warning(f"Se encontraron {len(inconsistencias)} expedientes con diferencia mayor a 2 días entre fechas en los últimos 30 días.")
                else:
                    st.success("No se encontraron inconsistencias significativas en las fechas de los últimos 30 días.")

        else:
            st.warning(f"No hay datos históricos para el módulo {selected_module}.")
            
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")

def get_last_date_from_db(module, collection):
    """Obtener la última fecha registrada para el módulo."""
    ultimo_registro = collection.find_one({"modulo": module}, sort=[("fecha", -1)])
    return ultimo_registro['fecha'] if ultimo_registro else None 