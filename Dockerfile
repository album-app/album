FROM ubuntu

COPY . /album

SHELL ["/bin/bash", "-l", "-c"]
RUN sed -e '/[ -z "$PS1" ] && return/s/^/#/g' -i /root/.bashrc
RUN apt update && apt install -y  git curl bzip2 ca-certificates
RUN mkdir -p /mamba/bin/
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/1.5.6 | tar -xvj -C /mamba/bin/ --strip-components=1 bin/micromamba
ENV MAMBA_ROOT_PREFIX="/mamba/bin/env"
ENV MAMBA_EXE="/mamba/bin/micromamba"
RUN $MAMBA_EXE shell init --shell bash
RUN echo "micromamba activate" >> /root/.bashrc

RUN micromamba install -y git python==3.14 pip -c conda-forge &&  cd /album && pip install . && album index

RUN chmod +x /album/docker_entrypoint.sh

ENTRYPOINT ["/album/docker_entrypoint.sh"]
LABEL MAINTAINER="Max Delbrueck Centrum for Molecular Medicine"
LABEL author="Jan Philipp Albrecht, Deborah Schmidt, Kyle Harrington"
LABEL comment="Album - spanning solutions across scales and tools"
