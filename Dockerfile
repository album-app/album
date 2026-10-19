FROM ubuntu:26.04

COPY . /album

SHELL ["/bin/bash", "-l", "-c"]
RUN sed -e '/[ -z "$PS1" ] && return/s/^/#/g' -i /root/.bashrc
RUN rm -rf /var/lib/apt/lists/* && apt-get update && apt-get install -y git curl bzip2 ca-certificates
RUN mkdir -p /mamba/bin/
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/2.5.0 | tar -xvj -C /mamba/bin/ --strip-components=1 bin/micromamba
ENV MAMBA_ROOT_PREFIX="/mamba/bin/env"
ENV MAMBA_EXE="/mamba/bin/micromamba"
RUN $MAMBA_EXE shell init --shell bash
RUN echo "micromamba activate" >> /root/.bashrc

# Packages pip installs together with album, none for the published image. album-docker's CI builds the image of an
# unreleased album with album-solution-api and album-environments from their dev branches (git+https://... URLs).
ARG ALBUM_DEV_DEPENDENCIES=""
RUN micromamba install -y git python=3.14 pip -c conda-forge &&  cd /album && pip install $ALBUM_DEV_DEPENDENCIES . && album index

RUN chmod +x /album/docker_entrypoint.sh

ENTRYPOINT ["/album/docker_entrypoint.sh"]
LABEL MAINTAINER="Max Delbrueck Centrum for Molecular Medicine"
LABEL author="Jan Philipp Albrecht, Deborah Schmidt, Kyle Harrington"
LABEL comment="Album - spanning solutions across scales and tools"
