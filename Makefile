FILENAME = thesis

all: thesis

pdf: thesis clean

thesis:
	pdflatex -draftmode $(FILENAME).tex
	biber $(FILENAME)
	pdflatex -draftmode $(FILENAME).tex
	pdflatex $(FILENAME).tex
	
clean:
	latexmk -c
	rm -rf $(FILENAME).{aux,bbl,bcf,blg,log,out,run.xml,synctex.gz,toc,fls,fdb_latexmk,pyg,glg-abr,glo-abr,gls-abr,glg,glo,gls,ist,lof,lot,flo,fln,fls,log,bbl-SAVE-ERROR} texput.log
