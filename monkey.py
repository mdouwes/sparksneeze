#!/usr/bin/env python3
"""
Monkey patch for testing Microsoft Fabric OneLake support in sparksneeze.
Apply this patch before using sparksneeze in Microsoft Fabric.

Usage:
    import monkey  # Apply the patch
    from sparksneeze import sparksneeze
    from sparksneeze.strategy import DropCreate
    # ... rest of your code
"""

def _is_fabric_onelake_path(self, path: str) -> bool:
    """Determine if this is a Microsoft Fabric OneLake path."""
    return "onelake.dfs.fabric.microsoft.com" in path.lower()


def _fabric_aware_write(original_write):
    """Wrapper for write method with Microsoft Fabric OneLake support."""
    def write(self, dataframe, mode):
        from sparksneeze.enums import WriteMode
        
        # Handle WriteMode enum
        mode_str = mode.value if isinstance(mode, WriteMode) else mode

        writer = dataframe.write.format("delta").mode(mode_str)

        # Apply Delta-specific options
        for key, value in self.options.items():
            writer = writer.option(key, value)

        writer.save(self.path)
    
    return write


def _fabric_aware_drop(original_drop):
    """Wrapper for drop method with Microsoft Fabric OneLake support."""
    def drop(self):
        try:
            if self.exists():
                if self._is_catalog_table():
                    # For catalog tables, use SQL DROP TABLE
                    validated_table_name = self._validate_identifier(self.path)
                    sql = f"DROP TABLE IF EXISTS {validated_table_name}"
                    self.spark_session.sql(sql)
                else:
                    if self._is_fabric_onelake_path(self.path):
                        try:
                            from delta.tables import DeltaTable
                            delta_table = DeltaTable.forPath(self.spark_session, self.path)
                            delta_table.delete()
                        except Exception:
                            pass
                    else:
                        hadoop_conf = (
                            self.spark_session.sparkContext._jsc.hadoopConfiguration()
                        )
                        fs = self.spark_session.sparkContext._jvm.org.apache.hadoop.fs.FileSystem.get(
                            hadoop_conf
                        )
                        path = (
                            self.spark_session.sparkContext._jvm.org.apache.hadoop.fs.Path(
                                self.path
                            )
                        )

                        if fs.exists(path):
                            fs.delete(path, True)
        except Exception as e:
            # If we can't drop the table, log warning but continue - the write will overwrite
            # Using print since logger may not be available in this context
            print(f"Warning: Could not drop Delta table: {e}")
    
    return drop


def _fabric_aware_init(original_init):
    """Wrapper for __init__ method to fix path resolution for OneLake."""
    def __init__(self, path: str, spark_session, **options):
        # Validate path before processing
        if not path or path.strip() == "":
            raise ValueError("Path cannot be empty")

        # Call parent __init__
        from sparksneeze.data_targets.base import DataTarget
        DataTarget.__init__(self, path, spark_session, **options)
        
        # Store original path for catalog table detection
        self._original_path = path.strip()
        
        if self._is_catalog_table_name(path):
            self.path = path.strip()
        elif self._is_fabric_onelake_path(path) or any(path.startswith(prefix) for prefix in ["s3://", "hdfs://", "abfss://", "gs://", "adl://"]):
            self.path = path.strip()
        else:
            from pathlib import Path
            self.path = str(Path(path).resolve())
    
    return __init__


def apply_fabric_patch():
    """Apply the Microsoft Fabric OneLake patch to sparksneeze."""
    try:
        from sparksneeze.data_targets.delta import DeltaTarget
        
        # Add the fabric path detection method
        DeltaTarget._is_fabric_onelake_path = _is_fabric_onelake_path
        
        # Store original methods
        original_write = DeltaTarget.write
        original_drop = DeltaTarget.drop
        original_init = DeltaTarget.__init__
        
        # Apply monkey patches
        DeltaTarget.write = _fabric_aware_write(original_write)
        DeltaTarget.drop = _fabric_aware_drop(original_drop)
        DeltaTarget.__init__ = _fabric_aware_init(original_init)
        
        print("✓ Microsoft Fabric OneLake monkey patch applied successfully!")
        
    except ImportError as e:
        print(f"✗ Failed to apply patch: {e}")
        print("Make sure sparksneeze is installed and available")
    except Exception as e:
        print(f"✗ Unexpected error applying patch: {e}")


# Automatically apply the patch when this module is imported
apply_fabric_patch()