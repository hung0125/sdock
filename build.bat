pyinstaller --onefile --noconsole sdock.py
rmdir /s /q build
move /y .\dist\sdock.exe .\
rmdir /s /q dist
del sdock.spec
pause