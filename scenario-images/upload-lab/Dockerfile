FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY main.go ./
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /upload

FROM alpine:3.20
RUN apk add --no-cache busybox && rm -rf /var/cache/apk/*
COPY flag.txt /flag.txt
COPY --from=build /upload /upload
VOLUME /srv/uploads
EXPOSE 80
ENTRYPOINT ["/upload"]