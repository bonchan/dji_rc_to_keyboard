# dji_rc_to_keyboard




build:
$ pyinstaller --onefile --console --name DroneController main.py



for dji rc plus 2 download https://gist.github.com/ifiokjr/b70882d3f1182ed48ec7eefa5c93a740

https://dl.google.com/android/repository/platform-tools-latest-windows.zip

notification
./adb.exe shell cmd notification post -t "Mission Recorder" --tag "DJI_U" 1 "Recording Started"


./adb.exe shell "monkey -p com.android.settings -c android.intent.category.LAUNCHER 1; sleep 1; msg='CRUISE ENABLED'; am start -a android.intent.action.MAIN -e msg \"$msg\""


