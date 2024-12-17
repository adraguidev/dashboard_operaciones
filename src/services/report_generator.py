class ReportGenerator:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def generate_excel(self, sheets_config: Dict[str, pd.DataFrame]) -> BytesIO:
        """Genera reportes Excel con múltiples hojas de manera estandarizada."""
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, df in sheets_config.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        output.seek(0)
        return output 