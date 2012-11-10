#!/bin/zsh
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

cd ankiqt
./tools/build_ui.sh
cd ..

cd anking
for form in *.ui; do
  pyuic4 $form -o ${form:r}.py
done
