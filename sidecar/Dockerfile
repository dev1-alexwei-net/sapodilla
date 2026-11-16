FROM golang:1.23-alpine AS builder
WORKDIR /src
COPY go.mod ./
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/sidecar .

FROM alpine:3.20
RUN addgroup -S app && adduser -S app -G app
COPY --from=builder /out/sidecar /usr/local/bin/sidecar
USER app
# Default sidecar port; override with ADDR at runtime.
EXPOSE 9090
ENTRYPOINT ["/usr/local/bin/sidecar"]
