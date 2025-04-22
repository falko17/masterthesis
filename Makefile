FILENAME = thesis
PRESFILENAME = presentation

all: thesis

pdf: thesis clean

thesis:
	pdflatex -shell-escape -draftmode $(FILENAME).tex
	$(MAKE) -f $(FILENAME).makefile
	biber $(FILENAME)
	makeglossaries $(FILENAME)
	pdflatex -shell-escape -draftmode $(FILENAME).tex
	pdflatex -shell-escape $(FILENAME).tex

presentation:
	pdflatex -shell-escape -draftmode $(PRESFILENAME).tex
	# $(MAKE) -f thesis.makefile
	# biber $(PRESFILENAME)
	pdflatex -shell-escape -draftmode $(PRESFILENAME).tex
	pdflatex -shell-escape $(PRESFILENAME).tex

clean:
	latexmk -c
	rm -rf {$(FILENAME),$(PRESFILENAME)}.{aux,auxlock,bbl,bcf,blg,cb,cb2,figlist,listing,lox,makefile,mw,'synctex(busy)',log,xdy,out,run.xml,synctex.gz,toc,fls,fdb_latexmk,pyg,glg-abr,glo-abr,gls-abr,glg,glo,gls,ist,lof,lot,flo,fln,fls,log,bbl-SAVE-ERROR} "$(FILENAME)-figure*" texput.log
