!macro customInstall
  DeleteRegKey HKCU "Software\Classes\managebac-sync"
  WriteRegStr SHELL_CONTEXT "Software\Classes\managebac-sync" "" "URL:managebac-sync"
  WriteRegStr SHELL_CONTEXT "Software\Classes\managebac-sync" "URL Protocol" ""
  WriteRegStr SHELL_CONTEXT "Software\Classes\managebac-sync\DefaultIcon" "" `"$INSTDIR\${APP_EXECUTABLE_FILENAME}",0`
  WriteRegStr SHELL_CONTEXT "Software\Classes\managebac-sync\shell\open\command" "" `"$INSTDIR\${APP_EXECUTABLE_FILENAME}" "%1"`
!macroend

!macro customUnInstall
  DeleteRegKey SHELL_CONTEXT "Software\Classes\managebac-sync"
  DeleteRegKey HKCU "Software\Classes\managebac-sync"
!macroend
