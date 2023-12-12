#!/bin/bash

# Inspired by
# https://medium.com/omi-uulm/how-to-run-containerized-bluetooth-applications-with-bluez-dced9ab767f6

# Start dbus and bluetooth services
echo -e "Starting dbus and bluetooth services"
service dbus start
service bluetooth start

# We must wait for bluetooth service to start
msg="Waiting for services to start..."
time=0
echo -n "$msg"
while [[ "$(pidof start-stop-daemon)" != "" ]]; do
	sleep 1
	time=$((time + 1))
	echo -en "\r$msg $time s"
done
echo -e "\r$msg done! (in $time s)"

# Reset adapter in case it was stuck from previous session
echo -e "Resetting bluetooth adapter"
hciconfig hci0 down
hciconfig hci0 up

echo -e "Starting plejd"
su plejd -c "python -m plejd_mqtt_ha --config $SETTINGS_DIR/$SETTINGS_FILE"
#tail -f /dev/null
