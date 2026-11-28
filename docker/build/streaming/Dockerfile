# lmelp-streaming : l'audio des émissions pour lmelp-mobile, derrière la clé
# d'écoute (ADR 0003). Le dossier audio de lmelp se monte en lecture seule sur
# /srv/audios ; le backend se joint sous le nom « backend » du réseau Docker.
FROM nginx:alpine

# curl pour le healthcheck
RUN apk add --no-cache curl

COPY docker/build/streaming/nginx.conf /etc/nginx/conf.d/default.conf
RUN mkdir -p /srv/audios /var/cache/nginx/cle

# Valide la configuration (échoue aussi si un proxy_pass vise un hôte en dur,
# non résolvable au build)
RUN nginx -t

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1
