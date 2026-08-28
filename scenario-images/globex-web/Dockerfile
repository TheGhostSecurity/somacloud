# ---- Build stage ----
FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY main.go ./
COPY static ./static
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /globex

# ---- Runtime stage: just the binary + CA certs ----
FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /globex /globex
EXPOSE 80
ENTRYPOINT ["/globex"]