from pathlib import Path
import sys
FILE_PATH = Path.cwd().joinpath('Py_DSSATTools')

sys.path.append(
    str(FILE_PATH.absolute())
)
