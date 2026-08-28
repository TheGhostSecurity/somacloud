FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY main.go ./
RUN go mod tidy && CGO_ENABLED=0 go build -ldflags="-s -w" -o /sqli

FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /sqli /sqli
EXPOSE 80
ENTRYPOINT ["/sqli"]