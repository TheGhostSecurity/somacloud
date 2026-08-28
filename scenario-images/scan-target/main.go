package main

import (
	"bufio"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"strings"
	"time"
)

const flag = "Globex{scanning_networks_2026}"

const ftpBanner = "220 ProFTPD 1.3.5e Server (Globex-FTP)\r\n"
const sshBanner = "SSH-2.0-OpenSSH_7.6p1 Ubuntu-4ubuntu0.7\r\n"

func main() {
	go bannerPort(21, ftpBanner)
	go bannerPort(22, sshBanner)
	go serveHTTP(80, "nginx/1.24.0", "PHP/8.2.3", "GlobexCMS 3.1", true)
	go serveHTTP(8080, "Apache/2.4.41 (Ubuntu)", "PHP/7.4.33", "", false)
	select {}
}

// bannerPort accepts TCP connections and immediately speaks a fingerprintable
// banner so nmap -sV can identify the service (FTP and SSH style).
func bannerPort(port int, banner string) {
	ln, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		log.Printf("port %d: %v", port, err)
		return
	}
	log.Printf("banner service listening on :%d", port)
	for {
		conn, err := ln.Accept()
		if err != nil {
			continue
		}
		go func(c net.Conn) {
			defer c.Close()
			_ = c.SetDeadline(time.Now().Add(4 * time.Second))
			if _, err := io.WriteString(c, banner); err != nil {
				return
			}
			r := bufio.NewReader(c)
			for {
				line, err := r.ReadString('\n')
				if err != nil {
					return
				}
				cmd := strings.ToUpper(strings.TrimSpace(line))
				if strings.HasPrefix(cmd, "FEAT") {
					_, _ = io.WriteString(c, "211-Features:\r\n AUTH TLS\r\n UTF8\r\n211 End\r\n")
				} else {
					_, _ = io.WriteString(c, "502 Command not implemented.\r\n")
				}
			}
		}(conn)
	}
}

// serveHTTP runs an HTTP listener with fingerprintable Server headers so
// nmap -sV pins the exact web server. Port 80 also hosts the robots.txt hint
// and the hidden capstone flag.
func serveHTTP(port int, server, poweredBy, generator string, withFlag bool) {
	mux := http.NewServeMux()

	if withFlag {
		mux.HandleFunc("GET /robots.txt", func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "text/plain; charset=utf-8")
			_, _ = io.WriteString(w, "User-agent: *\nDisallow: /hidden/\nDisallow: /server-status\n")
		})
		mux.HandleFunc("GET /hidden/flag.txt", func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "text/plain; charset=utf-8")
			_, _ = io.WriteString(w, flag+"\n")
		})
		mux.HandleFunc("GET /hidden/", func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = io.WriteString(w, "<h1>Globex internal staging</h1><p>flag: <a href=\"/hidden/flag.txt\">view</a></p>\n")
		})
		mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			_, _ = io.WriteString(w, "{\"status\":\"ok\",\"version\":\"2.0.1\"}\n")
		})
	}

	mux.HandleFunc("GET /", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = io.WriteString(w, "<!DOCTYPE html><html><head><title>Globex Global</title></head>"+
			"<body><h1>Globex Global</h1><p>Welcome to the Globex corporate portal.</p></body></html>\n")
	})

	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Server", server)
		if poweredBy != "" {
			w.Header().Set("X-Powered-By", poweredBy)
		}
		if generator != "" {
			w.Header().Set("X-Generator", generator)
		}
		mux.ServeHTTP(w, r)
	})

	log.Printf("http service listening on :%d (%s)", port, server)
	if err := http.ListenAndServe(fmt.Sprintf(":%d", port), handler); err != nil {
		log.Fatal(err)
	}
}