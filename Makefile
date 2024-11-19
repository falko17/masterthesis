FILENAME = thesis

all: thesis

pdf: thesis clean

thesis:
	pdflatex -shell-escape -draftmode $(FILENAME).tex
	biber $(FILENAME)
	pdflatex -shell-escape -draftmode $(FILENAME).tex
	pdflatex -shell-escape $(FILENAME).tex
	
clean:
	latexmk -c
	rm -rf $(FILENAME).{aux,auxlock,bbl,bcf,blg,cb,cb2,figlist,listing,lox,makefile,mw,'synctex(busy)',log,xdy,out,run.xml,synctex.gz,toc,fls,fdb_latexmk,pyg,glg-abr,glo-abr,gls-abr,glg,glo,gls,ist,lof,lot,flo,fln,fls,log,bbl-SAVE-ERROR} texput.log
