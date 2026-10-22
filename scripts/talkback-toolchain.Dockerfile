FROM i386/debian:bullseye
RUN apt-get update -qq \
 && apt-get install -y -qq libmpc3 libmpfr6 libgmp10 zlib1g \
 && ln -sf libmpfr.so.6 /usr/lib/i386-linux-gnu/libmpfr.so.4 \
 && rm -rf /var/lib/apt/lists/*
