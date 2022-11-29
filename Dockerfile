FROM continuumio/miniconda3:4.9.2
COPY . /album
RUN conda install git && pip install -e ./album
ENTRYPOINT ["album", "-h"]
LABEL MAINTAINER="Max Delbrueck Centrum for Molecular Medicine"
LABEL author="Jan Philipp Albrecht, Deborah Schmidt, Kyle Harrington, Lucas Rieckert"
LABEL comment="album - spanning solutions across scales and tools"