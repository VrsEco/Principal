FROM postgres:18

# Install pt_BR.UTF-8 locale required by the existing cluster
RUN apt-get update && apt-get install -y locales && \
    sed -i 's/# pt_BR.UTF-8 UTF-8/pt_BR.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=pt_BR.UTF-8 \
    LC_ALL=pt_BR.UTF-8 \
    LC_COLLATE=pt_BR.UTF-8 \
    LC_CTYPE=pt_BR.UTF-8 \
    LC_MESSAGES=pt_BR.UTF-8 \
    LC_MONETARY=pt_BR.UTF-8 \
    LC_NUMERIC=pt_BR.UTF-8 \
    LC_TIME=pt_BR.UTF-8
