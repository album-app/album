# syntax=docker/dockerfile:1
FROM continuumio/miniconda3:4.9.2
COPY . /album
RUN ["/bin/bash","-c", "conda env create -f /album/album.yml; echo conda activate album >> /root/.bashrc; chmod +x /album/docker/entrypoint.sh; chmod +x /album/docker/entrypoint-solution.sh"]
EXPOSE 8080
ENTRYPOINT ["/album/docker/entrypoint.sh"]
CMD ["server", "--port=8080", "--host=0.0.0.0"]
LABEL MAINTAINER="Max Delbrueck Centrum for Molecular Medicine"
LABEL author="Kyle Harrington, Jan Philipp Albrecht, Deborah Schmidt"
LABEL version="0.1.0"
LABEL comment="album - spanning solutions across scales and tools"
