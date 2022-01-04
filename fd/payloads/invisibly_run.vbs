REM invisibly (!) run the command provided in the first parameter
CreateObject("Wscript.Shell").Run """" & Wscript.Arguments(0) &  """", 0, False