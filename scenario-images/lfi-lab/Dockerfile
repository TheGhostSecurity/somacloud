FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY main.go ./
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /lfi

FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /lfi /lfi
COPY flag.txt /flag.txt
COPY pages /srv/www/
EXPOSE 80
ENTRYPOINT ["/lfi"]