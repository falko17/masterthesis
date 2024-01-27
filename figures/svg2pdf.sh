#!/bin/sh

set -eu

for i in ./*.svg; do
	echo "Converting $i..."
	inkscape -D "$i" -o "${i%.*}.pdf" #&& rm "$i"
done
