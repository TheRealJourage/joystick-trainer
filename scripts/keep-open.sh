#!/usr/bin/env bash
# Runs a command from a desktop icon and keeps the terminal open afterwards, so messages can be read.
"$@"
echo
read -r -p "Fenster schließen mit Enter. " _
