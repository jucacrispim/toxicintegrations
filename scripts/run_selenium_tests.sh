#!/bin/sh

export DISPLAY=:99
Xvfb :99  -ac -screen 0, 1368x768x24 &
ver=`chromedriver --version | cut -d' ' -f 2 | cut -d'.' -f1`
export CHROME_VERSION=$ver
behave tests/functional
status=$?
killall Xvfb
rm -f /tmp/.X99-lock
exit $status
