import os
import getpass
import json
import yaml

from mlflow_export_import.common.timestamp_utils import ts_now_seconds, ts_now_fmt_utc
from mlflow_export_import.common import filesystem as _fs
from mlflow_export_import.common.source_tags import ExportFields
from mlflow_export_import.common.pkg_version import get_version
from databricks.sdk.runtime import *


export_file_version = "2"


def _mk_system_attr(script):
    """
    Create system JSON stanza containing internal export information.
    """
    import mlflow
    import platform
    dct = {
        "package_version": get_version(),
        "script": os.path.basename(script),
        "export_file_version": export_file_version,
        "export_time": ts_now_seconds,
        "_export_time": ts_now_fmt_utc,
        "mlflow_version": mlflow.__version__,
        "mlflow_tracking_uri": mlflow.get_tracking_uri(),
        "platform": {
            "python_version": platform.python_version(),
            "system": platform.system(),
            "processor": platform.processor()
        },
        "user": getpass.getuser(),
    }
    dbr = os.environ.get("DATABRICKS_RUNTIME_VERSION", None)
    if dbr:
        dct2 = {
            "databricks": {
                 "DATABRICKS_RUNTIME_VERSION": dbr,
            }
        }
        dct = { **dct, **dct2 }
    return { ExportFields.SYSTEM: dct }


def write_export_file(dir, file, script, mlflow_attr, info_attr=None):
    """
    Write standard formatted JSON file.
    """
    dir = dir #_fs.mk_dbfs_path(dir)
    path = os.path.join(dir, file)
    info_attr = { ExportFields.INFO: info_attr} if info_attr else {}
    mlflow_attr = { ExportFields.MLFLOW: mlflow_attr}
    mlflow_attr = { **_mk_system_attr(script), **info_attr, **mlflow_attr }
    # os.makedirs(dir, exist_ok=True)
    dbutils.fs.mkdirs(dir)
    write_file(path, mlflow_attr)


def _is_yaml(path, file_type=None):
    return any(path.endswith(x) for x in [".yaml",".yml"]) or file_type in ["yaml","yml"]


def write_file(path, content, file_type=None):
    """
    Write to JSON, YAML or text file.
    """
    ## path = _fs.mk_local_path(path)
    # if path.endswith(".json"):
    #     with open(path, "w", encoding="utf-8") as f:
    #         f.write(json.dumps(content, indent=2)+"\n")
    # elif _is_yaml(path, file_type):
    #     with open(path, "w", encoding="utf-8") as f:
    #         yaml.dump(content, f)
    # else:
    #     with open(path, "wb" ) as f:
    #         f.write(content)
    if path.startswith("dbfs:/"):
        if path.endswith(".json"):
            json_content = json.dumps(content, indent=2) + "\n"
            dbutils.fs.put(path, json_content, overwrite=True)
        elif _is_yaml(path, file_type):
            yaml_content = yaml.dump(content)
            dbutils.fs.put(path, yaml_content, overwrite=True)
        else:
            if isinstance(content, str):
                dbutils.fs.put(path, content, overwrite=True)
            else:
                raise ValueError("Binary content is not supported for dbfs:/ paths.")
    else:
        # Fallback for local file paths
        if path.endswith(".json"):
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps(content, indent=2) + "\n")
        elif _is_yaml(path, file_type):
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(content, f)
        else:
            with open(path, "wb") as f:
                f.write(content)


def read_file(path, file_type=None):
    """
    Read a JSON, YAML or text file.
    """
    # with open(_fs.mk_local_path(path), "r", encoding="utf-8") as f:
    #     if path.endswith(".json"):
    #         return json.loads(f.read())
    #     elif _is_yaml(path, file_type):
    #         return yaml.safe_load(f)
    #     else:
    #         return f.read()
    if path.startswith("dbfs:/"):
        # Use Spark for reading files
        if path.endswith(".json"):
            # Read JSON content as a string
            content = spark.read.text(path).collect()
            json_content = "\n".join(row.value for row in content)
            return json.loads(json_content)
        elif _is_yaml(path, file_type):
            # Read YAML content as a string
            content = spark.read.text(path).collect()
            yaml_content = "\n".join(row.value for row in content)
            return yaml.safe_load(yaml_content)
        else:
            # For plain text files
            content = spark.read.text(path).collect()
            return "\n".join(row.value for row in content)
    else:
        # Fallback for local file paths
        with open(path, "r", encoding="utf-8") as f:
            if path.endswith(".json"):
                return json.loads(f.read())
            elif _is_yaml(path, file_type):
                return yaml.safe_load(f)
            else:
                return f.read()


def get_info(export_dct):
    return export_dct[ExportFields.INFO]


def get_mlflow(export_dct):
    return export_dct[ExportFields.MLFLOW]


def read_file_mlflow(path):
    dct = read_file(path)
    return dct[ExportFields.MLFLOW]


def mk_manifest_json_path(input_dir, filename):
    return os.path.join(input_dir, filename)
