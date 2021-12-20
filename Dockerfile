# syntax=docker/dockerfile:1
FROM continuumio/miniconda3:4.9.2
COPY . /album
RUN ["/bin/bash","-c", "conda env create -f /album/album.yml; echo conda activate album >> /root/.bashrc; chmod +x /album/src/album/docker/entrypoint.sh; chmod +x /album/src/album/docker/entrypoint-solution.sh"]
EXPOSE 8080
ENTRYPOINT ["/album/src/album/docker/entrypoint.sh"]
CMD ["server", "--port=8080", "--host=0.0.0.0"]
LABEL MAINTAINER="Max Delbrueck Centrum for Molecular Medicine"
LABEL author="Jan Philipp Albrecht, Deborah Schmidt, Kyle Harrington"
LABEL comment="album - spanning solutions across scales and tools"
