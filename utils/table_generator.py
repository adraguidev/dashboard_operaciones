def generate_table_multiple_years(data, selected_years, selected_evaluators=None):
    """
    Generar tabla resumen para múltiples años.
    """
    filtered_data = data[data['Anio'].isin(selected_years)]
    if selected_evaluators:
        filtered_data = filtered_data[filtered_data['EVALASIGN'].isin(selected_evaluators)]
    
    summary = filtered_data.groupby(['EVALASIGN', 'Anio']).agg(
        Pendientes=('Evaluado', lambda x: (x == 'NO').sum())
    ).unstack(fill_value=0)
    
    summary.columns = summary.columns.droplevel()
    summary['Total'] = summary.sum(axis=1)
    summary = summary[summary['Total'] > 0].sort_values(by='Total', ascending=False)
    summary.columns = summary.columns.astype(str)
    
    return summary.reset_index()

def generate_table_single_year(data, selected_year, selected_evaluators=None):
    """
    Generar tabla resumen para un solo año.
    """
    months = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    
    filtered_data = data[data['Anio'] == selected_year]
    if selected_evaluators:
        filtered_data = filtered_data[filtered_data['EVALASIGN'].isin(selected_evaluators)]
    
    summary = filtered_data.groupby(['EVALASIGN', 'Mes']).agg(
        Pendientes=('Evaluado', lambda x: (x == 'NO').sum())
    ).unstack(fill_value=0)
    
    summary.columns = [months[col] for col in summary.columns.droplevel()]
    summary['Total'] = summary.sum(axis=1)
    summary = summary[summary['Total'] > 0].sort_values(by='Total', ascending=False)
    summary.columns = summary.columns.astype(str)
    
    return summary.reset_index() 