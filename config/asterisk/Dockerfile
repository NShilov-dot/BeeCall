# Builds Asterisk 22 LTS from source with chan_websocket enabled.
# chan_websocket is required for Dograh's external-media streaming —
# see docs/integrations/telephony/asterisk-ari.mdx.

# `22-current` always tracks the latest stable Asterisk 22.x release on
# downloads.asterisk.org. The actual version is read from the tarball at
# build time and stamped into /etc/asterisk-version inside the runtime.
ARG ASTERISK_VERSION=22-current

FROM debian:12-slim AS builder
ARG ASTERISK_VERSION

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        file \
        git \
        libcurl4-openssl-dev \
        libedit-dev \
        libgsm1-dev \
        libjansson-dev \
        libncurses-dev \
        libnewt-dev \
        libogg-dev \
        libpopt-dev \
        libresample1-dev \
        libspandsp-dev \
        libspeex-dev \
        libspeexdsp-dev \
        libsqlite3-dev \
        libsrtp2-dev \
        libssl-dev \
        libtool \
        libvorbis-dev \
        libxml2-dev \
        libxslt1-dev \
        pkg-config \
        unixodbc-dev \
        uuid-dev \
        wget \
        xmlstarlet \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src
RUN curl -fsSL "https://downloads.asterisk.org/pub/telephony/asterisk/asterisk-${ASTERISK_VERSION}.tar.gz" \
      -o asterisk.tgz \
    && tar -xzf asterisk.tgz \
    && rm asterisk.tgz \
    && extracted="$(find . -maxdepth 1 -type d -name 'asterisk-*' | head -1)" \
    && test -n "$extracted" \
    && mv "$extracted" asterisk \
    && echo "$extracted" | sed 's|^\./asterisk-||' > /usr/src/asterisk-version.txt

WORKDIR /usr/src/asterisk
RUN contrib/scripts/get_mp3_source.sh || true

RUN ./configure \
        --with-jansson-bundled \
        --with-pjproject-bundled \
        --without-dahdi \
        --disable-xmldoc

# Pull menuselect defaults, then explicitly enable chan_websocket and
# res_websocket_client (these are off by default in some 22.x point releases).
RUN make menuselect.makeopts \
    && menuselect/menuselect --enable chan_websocket --enable res_websocket_client menuselect.makeopts \
    && menuselect/menuselect --enable CORE-SOUNDS-EN-ULAW menuselect.makeopts \
    && menuselect/menuselect --enable MOH-OPSOUND-ULAW menuselect.makeopts

# Bundled pjproject's submake races on parallel builds (especially aarch64),
# so build third-party deps single-threaded first, then the rest in parallel.
RUN make -j1 third-party \
    && make -j"$(nproc)" \
    && make install \
    && make samples \
    && make config

FROM debian:12-slim AS runtime
ARG ASTERISK_VERSION

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        libcurl4 \
        libedit2 \
        libgsm1 \
        libjansson4 \
        libncurses6 \
        libnewt0.52 \
        libogg0 \
        libpopt0 \
        libresample1 \
        libspandsp2 \
        libspeex1 \
        libspeexdsp1 \
        libsqlite3-0 \
        libsrtp2-1 \
        libssl3 \
        libvorbis0a \
        libxml2 \
        libxslt1.1 \
        unixodbc \
        uuid-runtime \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r asterisk \
    && useradd -r -g asterisk -d /var/lib/asterisk -s /sbin/nologin asterisk

# Copy Asterisk runtime artifacts produced by the builder.
COPY --from=builder /etc/asterisk /etc/asterisk
COPY --from=builder /usr/sbin/asterisk /usr/sbin/asterisk
COPY --from=builder /usr/sbin/safe_asterisk /usr/sbin/safe_asterisk
COPY --from=builder /usr/sbin/astgenkey /usr/sbin/astgenkey
COPY --from=builder /usr/lib/asterisk /usr/lib/asterisk
# Asterisk installs its own libs (libasteriskssl.so.1, libasteriskpj.so.2)
# alongside the binary — runtime won't start without them on the linker path.
COPY --from=builder /usr/lib/libasterisk*.so* /usr/lib/
RUN ldconfig
COPY --from=builder /var/lib/asterisk /var/lib/asterisk
COPY --from=builder /var/spool/asterisk /var/spool/asterisk
COPY --from=builder /var/log/asterisk /var/log/asterisk
COPY --from=builder /var/run/asterisk /var/run/asterisk

RUN chown -R asterisk:asterisk \
        /etc/asterisk \
        /var/lib/asterisk \
        /var/spool/asterisk \
        /var/log/asterisk \
        /var/run/asterisk

# 8088: ARI HTTP / WebSocket
# 5060/udp,5060/tcp: SIP signalling (PJSIP)
# 10000-10100/udp: RTP media (narrow range for local dev)
EXPOSE 8088/tcp 5060/udp 5060/tcp 10000-10100/udp

USER asterisk
WORKDIR /var/lib/asterisk

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/sbin/asterisk", "-f", "-U", "asterisk", "-G", "asterisk", "-vvvdddf", "-T", "-W"]
