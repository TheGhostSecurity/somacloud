# ---- Build stage ----
FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY main.go ./
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /scan-target

# ---- Runtime stage: just the binary + CA certs ----
FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /scan-target /scan-target
EXPOSE 21 22 80 8080
ENTRYPOINT ["/scan-target"]