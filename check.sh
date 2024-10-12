#!/bin/sh

rg -e 'e\.g\.' -e 'i\.e\.' -e 'texttt' -- *.tex content/*.tex
