FROM quay.io/keycloak/keycloak:26.7.3 AS builder
ENV KC_DB=postgres
ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true
ENV JAVA_OPTS_KC_HEAP="-XX:MaxRAMPercentage=30 -XX:InitialRAMPercentage=20"
WORKDIR /opt/keycloak
RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:26.7.3
COPY --from=builder /opt/keycloak/ /opt/keycloak/
