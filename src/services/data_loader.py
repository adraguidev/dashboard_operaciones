class DataLoader:
    @staticmethod
    def load_module_data(module_name: str) -> pd.DataFrame:
        """Carga datos de cualquier módulo de manera unificada."""
        if module_name == 'CCM-LEY':
            return DataLoader._load_ccm_ley_data()
        elif module_name == 'SPE':
            return DataLoader._load_spe_data()
        else:
            return DataLoader._load_consolidated_data(module_name) 