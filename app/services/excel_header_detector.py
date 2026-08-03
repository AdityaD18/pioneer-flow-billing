import pandas as pd

class ExcelHeaderDetector:
    """Scans Excel worksheets to locate valid header rows using synonym matching."""

    @staticmethod
    def detect_headers_and_df(file_path, sheet_name, mandatory_synonym_groups):
        """Scans the first 30 rows of a sheet to locate the header row matching at least one synonym from each group."""
        if hasattr(file_path, 'seek'):
            file_path.seek(0)
        df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=30)
        
        header_row_idx = None
        for i, row in df_raw.iterrows():
            row_str = [str(val).strip().lower() for val in row.values if pd.notna(val)]
            
            matched_groups = 0
            for group in mandatory_synonym_groups:
                if any(any(syn in cell_str for cell_str in row_str) for syn in group):
                    matched_groups += 1
            
            if matched_groups >= len(mandatory_synonym_groups):
                header_row_idx = i
                break
                
        if header_row_idx is None:
            raise ValueError(f"Could not find a valid header row containing part numbers in sheet '{sheet_name}'.")
            
        if hasattr(file_path, 'seek'):
            file_path.seek(0)
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row_idx)
        df.columns = [str(c).strip() for c in df.columns]
        return df

    @staticmethod
    def find_matching_column(df_cols, synonym_list):
        """Helper to find column key by exact match first, then substring match."""
        # Exact match (case insensitive)
        for c in df_cols:
            c_clean = str(c).lower().strip()
            if c_clean in synonym_list:
                return c
        # Substring match
        for c in df_cols:
            c_clean = str(c).lower().strip()
            if any(syn in c_clean for syn in synonym_list):
                return c
        return None
