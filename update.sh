#!/bin/zsh
# Copyright muflax <mail@muflax.com>, 2010
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

cd libanki
git pull
cd ..

cd ankiqt
git pull
./tools/build_ui.sh
cd ..

cd anking
for form in *.ui; do
  pyuic4 $form -o ${form:r}.py
done
