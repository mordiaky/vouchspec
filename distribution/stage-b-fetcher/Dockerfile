FROM alpine/git:v2.52.0@sha256:4a0e72d49596a1f5d3701aeedafdadc5c0da4062be4657c7bdc4017387f591cc

COPY distribution/stage-b-fetcher/fetch.sh /usr/local/bin/vouchspec-fetch
RUN chmod 0555 /usr/local/bin/vouchspec-fetch

USER 65532:65532
ENTRYPOINT ["/usr/local/bin/vouchspec-fetch"]
