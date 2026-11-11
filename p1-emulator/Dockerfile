ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 \
    && python3 -m venv /opt/p1-emulator \
    && /opt/p1-emulator/bin/pip install --no-cache-dir \
        aiohttp==3.13.3 \
        zeroconf==0.148.0

COPY rootfs /
COPY p1_emulator /opt/p1-emulator/app/p1_emulator
RUN chmod a+x /etc/services.d/p1-emulator/run

ENV PYTHONPATH=/opt/p1-emulator/app

LABEL \
    org.opencontainers.image.title="Home Assistant App: P1 Meter Emulator" \
    org.opencontainers.image.description="Expose Home Assistant sensors as a HomeWizard P1 Meter" \
    org.opencontainers.image.source="https://github.com/mnederlof/homeassistant-p1-emulator"
