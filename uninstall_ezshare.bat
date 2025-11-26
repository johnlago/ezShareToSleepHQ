@ECHO OFF

rmdir /s /q %USERPROFILE%\.venv\ezshare_resmed
del %USERPROFILE%\.local\bin\ezshare_resmed.cmd
del %USERPROFILE%\.local\bin\ezshare_resmed.py
del %USERPROFILE%\.local\bin\sleephq_uploader.py
del %USERPROFILE%\.local\bin\sleephq_client.py
echo ezshare_resmed uninstalled