import os
import win32com.client

def manejar_reportes():
    def procesar_carpeta(carpeta, nombre_hoja):
        # Configuración y rutas
        carpeta_path = os.path.abspath(f"./manejo_reportes/{carpeta}")
        archivo_pend = os.path.join(carpeta_path, f"{carpeta}PEND.xlsx")
        archivo_asignaciones = os.path.join(carpeta_path, f"ASIGNACIONES.xlsx")

        if not os.path.exists(archivo_pend) or not os.path.exists(archivo_asignaciones):
            print(f"Archivos faltantes en {carpeta}.")
            return

        try:
            print(f"Procesando carpeta: {carpeta}...")

            # Abrir archivo de asignaciones
            wb_asignaciones = excel.Workbooks.Open(archivo_asignaciones)

            # Verificar y eliminar rango nombrado si ya existe
            for name in wb_asignaciones.Names:
                if name.Name == f"CONSOLIDADO_{carpeta}_X_EVAL":
                    name.Delete()
                    print(f"Rango nombrado 'CONSOLIDADO_{carpeta}_X_EVAL' eliminado.")

            # Eliminar hoja CONSOLIDADO si ya existe
            for sheet in wb_asignaciones.Sheets:
                if sheet.Name == f"CONSOLIDADO_{carpeta}_X_EVAL":
                    sheet.Delete()
                    print(f"Hoja 'CONSOLIDADO_{carpeta}_X_EVAL' eliminada.")

            # Limpiar la pestaña REPORTADO_SIM
            sheet_reportado = wb_asignaciones.Sheets("REPORTADO_SIM")
            if sheet_reportado.ListObjects.Count > 0:
                table = sheet_reportado.ListObjects(1)
                if table.DataBodyRange:
                    table.DataBodyRange.ClearContents()
                    print(f"Datos eliminados en REPORTADO_SIM de {carpeta}.")
            else:
                print(f"No se encontró ninguna tabla en REPORTADO_SIM de {carpeta}.")

            # Abrir archivo de pendientes
            wb_pend = excel.Workbooks.Open(archivo_pend)
            sheet_pend = wb_pend.Sheets(1)

            # Identificar las columnas según la carpeta
            if carpeta == "SOL":
                col_tramite, col_nombre = "F", "X"
            else:
                col_tramite, col_nombre = "F", "AG"

            # Leer los datos de pendientes en memoria
            last_row_pend = sheet_pend.Cells(sheet_pend.Rows.Count, col_tramite).End(-4162).Row
            tramites = sheet_pend.Range(f"{col_tramite}4:{col_tramite}{last_row_pend}").Value
            nombres = sheet_pend.Range(f"{col_nombre}4:{col_nombre}{last_row_pend}").Value

            # Validar y filtrar los datos
            datos_filtrados = [
                (tramite[0], nombre[0])
                for tramite, nombre in zip(tramites, nombres)
                if tramite and tramite[0] and isinstance(tramite[0], str) and tramite[0].startswith(("LM", "LS", "MR", "LN"))
            ]

            # Escribir datos filtrados en REPORTADO_SIM
            if datos_filtrados:
                start_cell = sheet_reportado.Cells(2, 1)
                end_cell = sheet_reportado.Cells(1 + len(datos_filtrados), 2)
                rango = sheet_reportado.Range(start_cell, end_cell)
                rango.Value = datos_filtrados
                print(f"{len(datos_filtrados)} registros transferidos a REPORTADO_SIM en {carpeta}.")

            # Crear hoja CONSOLIDADO
            new_sheet = wb_asignaciones.Sheets.Add(After=wb_asignaciones.Sheets(wb_asignaciones.Sheets.Count))
            new_sheet.Name = f"CONSOLIDADO_{carpeta}_X_EVAL"

            # Consolidar datos de IDENTIFICADOS y REPORTADO_SIM
            sheet_identificados = wb_asignaciones.Sheets("IDENTIFICADOS")
            last_row_identificados = sheet_identificados.Cells(sheet_identificados.Rows.Count, 1).End(-4162).Row
            datos_identificados = sheet_identificados.Range(f"A2:B{last_row_identificados}").Value

            # Copiar encabezados a la nueva hoja
            new_sheet.Range("A1:B1").Value = [["EXPEDIENTE", "EVALUADOR"]]

            # Combinar datos en memoria
            datos_consolidados = []
            if datos_identificados:
                datos_consolidados.extend(datos_identificados)
            if datos_filtrados:
                datos_consolidados.extend(datos_filtrados)

            # Escribir datos consolidados en la nueva hoja
            if datos_consolidados:
                start_cell = new_sheet.Cells(2, 1)
                end_cell = new_sheet.Cells(1 + len(datos_consolidados), 2)
                rango = new_sheet.Range(start_cell, end_cell)
                rango.Value = datos_consolidados

            # Crear una tabla en la nueva hoja
            last_row_consolidado = len(datos_consolidados) + 1
            rango_tabla = new_sheet.Range(f"A1:B{last_row_consolidado}")
            new_sheet.ListObjects.Add(1, rango_tabla, None, True).Name = f"CONSOLIDADO_{carpeta}_X_EVAL"
            print(f"Consolidado creado en {carpeta}.")

            # Guardar los cambios
            wb_asignaciones.Save()

            # Cerrar los archivos
            wb_pend.Close(False)
            wb_asignaciones.Close(True)

        except Exception as e:
            print(f"Error procesando la carpeta {carpeta}: {e}")

    # Inicia Excel
    excel = win32com.client.Dispatch("Excel.Application")
    excel.DisplayAlerts = False  # Desactiva los diálogos para eliminar hojas sin confirmación
    excel.Visible = False

    # Procesar carpetas
    try:
        procesar_carpeta("CCM", "CONSOLIDADO_CCM_X_EVAL")
        procesar_carpeta("PRR", "CONSOLIDADO_PRR_X_EVAL")
        procesar_carpeta("SOL", "CONSOLIDADO_SOL_X_EVAL")
    finally:
        excel.DisplayAlerts = True
        excel.Quit()

    print("Proceso completado.")
