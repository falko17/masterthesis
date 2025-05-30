#!/bin/env perl

# Parts taken from Alexander Povel's LaTeX Cookbook .latexmkrc file.

# option 2 is same as 1 (run biber when necessary), but also deletes the
# regeneratable bbl-file in a clenaup (`latexmk -c`).
$bibtex_use = 2;

# Change default `biber` call, help catch errors faster/clearer. See
# https://web.archive.org/web/20200526101657/https://www.semipol.de/2018/06/12/latex-best-practices.html#database-entries
$biber = "biber --validate-datamodel %O %S";

# Let latexmk know about autogenerated files.
push @generated_exts, 'loe', 'lol', 'lor', 'run.xml', 'glg', 'glstex';
$clean_ext = "%R-*.glstex %R_contourtmp*.*";

$pdflatex = 'pdflatex --shell-escape %O %S';
