cls
call pip uninstall -y dbacademy-gems
call pip uninstall -y dbacademy-rest
pause
call pip install git+https://github.com/databricks-academy/dbacademy-gems@dev --no-cache-dir
call pip install git+https://github.com/databricks-academy/dbacademy-rest --no-cache-dir