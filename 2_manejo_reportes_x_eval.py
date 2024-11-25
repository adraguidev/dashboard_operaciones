import os
import win32com.client

def procesar_carpeta(carpeta, nombre_hoja):
    # Rutas de los archivos
    carpeta_path = os.path.abspath(f"./manejo_reportes/{carpeta}")
    archivo_pend = os.path.join(carpeta_path, f"{carpeta}PEND.xlsx")
    archivo_asignaciones = os.path.join(carpeta_path, f"ASIGNACIONES.xlsx")

    # Verificar que los archivos existen
    if not os.path.exists(archivo_pend):
        print(f"El archivo {archivo_pend} no existe. Saltando carpeta {carpeta}.")
        return
    if not os.path.exists(archivo_asignaciones):
        print(f"El archivo {archivo_asignaciones} no existe. Saltando carpeta {carpeta}.")
        return

    # Intentar abrir el archivo de asignaciones
    try:
        print(f"Procesando carpeta {carpeta}...")
        wb_asignaciones = excel.Workbooks.Open(archivo_asignaciones)
    except Exception as e:
        print(f"No se pudo abrir el archivo {archivo_asignaciones}: {e}. Saltando carpeta {carpeta}.")
        return

    # Eliminar cualquier rango nombrado o tabla con el nombre CONSOLIDADO
    try:
        wb_asignaciones.Names(f"CONSOLIDADO_{carpeta}_X_EVAL").Delete()
        print(f"Rango nombrado CONSOLIDADO_{carpeta}_X_EVAL eliminado.")
    except:
        print(f"No se encontró un rango nombrado CONSOLIDADO_{carpeta}_X_EVAL.")

    # Eliminar la hoja CONSOLIDADO si existe
    sheet_to_delete = None
    for sheet in wb_asignaciones.Sheets:
        if sheet.Name == f"CONSOLIDADO_{carpeta}_X_EVAL":
            sheet_to_delete = sheet
            break

    if sheet_to_delete:
        sheet_to_delete.Delete()
        print(f"Hoja CONSOLIDADO_{carpeta}_X_EVAL eliminada.")

    # Limpiar la pestaña REPORTADO_SIM
    sheet_reportado = wb_asignaciones.Sheets("REPORTADO_SIM")
    if sheet_reportado.ListObjects.Count > 0:
        table_reportado = sheet_reportado.ListObjects(1)
        if table_reportado.DataBodyRange is not None:  # Verificar si la tabla tiene datos
            table_reportado.DataBodyRange.ClearContents()
            print(f"Todos los registros de REPORTADO_SIM en {carpeta} eliminados.")
        else:
            print(f"No hay datos en la tabla de REPORTADO_SIM en {carpeta}.")
    else:
        print(f"No se encontró ninguna tabla en REPORTADO_SIM en {carpeta}.")

    # Abrir el archivo de pendientes
    wb_pend = excel.Workbooks.Open(archivo_pend)
    sheet_pend = wb_pend.Sheets(1)  # Primera hoja

    # Identificar las columnas según la carpeta
    if carpeta == "SOL":
        col_tramite = "F"  # Columna para TRÁMITE
        col_nombre = "X"   # Columna para NOMBRE/OPERADOR
    else:
        col_tramite = "F"  # Columna para TRÁMITE
        col_nombre = "AG"  # Columna para NOMBRE/OPERADOR

    # Leer los datos de pendientes en memoria
    last_row_pend = sheet_pend.Cells(sheet_pend.Rows.Count, col_tramite).End(-4162).Row
    tramites = sheet_pend.Range(f"{col_tramite}4:{col_tramite}{last_row_pend}").Value
    nombres = sheet_pend.Range(f"{col_nombre}4:{col_nombre}{last_row_pend}").Value

    # Filtrar y procesar los datos en memoria
    datos_filtrados = [
        (tramite[0], nombre[0])
        for tramite, nombre in zip(tramites, nombres)
        if tramite[0] and nombre[0] and tramite[0].startswith(("LM", "LS", "MR", "LN"))
    ]

    # Escribir los datos filtrados en REPORTADO_SIM
    if datos_filtrados:
        start_cell = sheet_reportado.Cells(2, 1)  # Comienza en la fila 2, columna 1
        end_cell = sheet_reportado.Cells(1 + len(datos_filtrados), 2)  # Fila final
        rango = sheet_reportado.Range(start_cell, end_cell)
        rango.Value = datos_filtrados
    print(f"{len(datos_filtrados)} registros transferidos a REPORTADO_SIM en {carpeta}.")

    # Crear la hoja CONSOLIDADO
    new_sheet = wb_asignaciones.Sheets.Add(After=wb_asignaciones.Sheets(wb_asignaciones.Sheets.Count))
    new_sheet.Name = f"CONSOLIDADO_{carpeta}_X_EVAL"

    # Consolidar IDENTIFICADOS y REPORTADO_SIM
    sheet_identificados = wb_asignaciones.Sheets("IDENTIFICADOS")
    last_row_identificados = sheet_identificados.Cells(sheet_identificados.Rows.Count, 1).End(-4162).Row

    # Leer datos de IDENTIFICADOS
    datos_identificados = sheet_identificados.Range(f"A2:B{last_row_identificados}").Value

    # Copiar encabezados
    new_sheet.Range("A1:B1").Value = [["EXPEDIENTE", "EVALUADOR"]]

    # Combinar los datos en memoria
    datos_consolidados = []
    if datos_identificados:
        datos_consolidados.extend(datos_identificados)
    if datos_filtrados:
        datos_consolidados.extend(datos_filtrados)

    # Escribir los datos consolidados en la hoja
    if datos_consolidados:
        start_cell = new_sheet.Cells(2, 1)  # Comienza en la fila 2
        end_cell = new_sheet.Cells(1 + len(datos_consolidados), 2)
        rango = new_sheet.Range(start_cell, end_cell)
        rango.Value = datos_consolidados

    # Crear una tabla en la hoja consolidada
    last_row_consolidado = len(datos_consolidados) + 1
    rango_tabla = new_sheet.Range(f"A1:B{last_row_consolidado}")
    new_sheet.ListObjects.Add(1, rango_tabla, None, True).Name = f"CONSOLIDADO_{carpeta}_X_EVAL"

    print(f"Consolidación completada en {carpeta}.")

    # Guardar los cambios
    wb_asignaciones.Save()

    # Cerrar los archivos
    wb_pend.Close(False)
    wb_asignaciones.Close(True)


# Inicia Excel
excel = win32com.client.Dispatch("Excel.Application")
excel.DisplayAlerts = False  # Desactiva los diálogos para eliminar hojas sin confirmación
excel.Visible = False  # Cambiar a True si deseas visualizar el proceso en Excel

# Cierra el libro inicial "Libro1" si existe, sin guardar
if excel.Workbooks.Count > 0:
    for workbook in excel.Workbooks:
        if workbook.Name == "Libro1":
            workbook.Close(SaveChanges=False)
            print("Libro1 cerrado automáticamente.")

try:
    # Procesar las carpetas CCM, PRR y SOL
    procesar_carpeta("CCM", "CONSOLIDADO_CCM_X_EVAL")
    procesar_carpeta("PRR", "CONSOLIDADO_PRR_X_EVAL")
    procesar_carpeta("SOL", "CONSOLIDADO_SOL_X_EVAL")

finally:
    # Restaurar las alertas y cerrar Excel
    excel.DisplayAlerts = True
    excel.Quit()

print("Proceso completado.")

