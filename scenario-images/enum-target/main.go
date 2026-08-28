package main

import (
	"bufio"
	"io"
	"log"
	"net"
	"strings"
	"time"
)

// SMTP responder (banner + VRFY/EXPN enumeration emulation).

var smtpUsers = map[string]bool{
	"bsmith":  true,
	"jtaylor": true,
	"jdoe":    true,
	"globex":  true,
}

var smtpAliases = map[string][]string{
	"webteam": {"bsmith", "jtaylor"},
	"it":      {"globex"},
}

func smtpServer() {
	ln, err := net.Listen("tcp", ":25")
	if err != nil {
		log.Printf("smtp listen :25: %v", err)
		return
	}
	log.Printf("smtp listening on :25")
	for {
		conn, err := ln.Accept()
		if err != nil {
			continue
		}
		go handleSMTP(conn)
	}
}

func handleSMTP(conn net.Conn) {
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(60 * time.Second))
	r := bufio.NewReader(conn)
	wr := func(s string) { _, _ = io.WriteString(conn, s) }
	wr("220 globex.local ESMTP GlobexMail 2.3.1\r\n")

	for {
		line, err := r.ReadString('\n')
		if err != nil {
			return
		}
		line = strings.TrimRight(line, "\r\n")
		cmd := strings.ToUpper(strings.TrimSpace(line))
		arg := strings.TrimSpace(strings.TrimLeft(line, cmd))
		word := cmd
		if i := strings.Index(cmd, " "); i >= 0 {
			word = cmd[:i]
		}

		switch word {
		case "EHLO":
			wr("250-globex.local\r\n" +
				"250-PIPELINING\r\n" +
				"250-SIZE 10240000\r\n" +
				"250-VRFY\r\n" +
				"250-EXPN\r\n" +
				"250-8BITMIME\r\n" +
				"250 ENHANCEDSTATUSCODES\r\n")
		case "HELO":
			wr("250 globex.local\r\n")
		case "VRFY":
			u := strings.ToLower(strings.TrimSuffix(strings.SplitN(arg, "@", 2)[0], ">"))
			u = strings.TrimPrefix(u, "<")
			if smtpUsers[u] {
				wr("252 2.1.5 " + u + " <" + u + "@globex.local>" + "\r\n")
			} else {
				wr("550 5.1.1 <" + arg + ">: Recipient address rejected: User unknown\r\n")
			}
		case "EXPN":
			list := strings.ToLower(strings.TrimSpace(arg))
			if members, ok := smtpAliases[list]; ok {
				wr("250 " + strings.Join(members, "@globex.local, ") + "@globex.local\r\n")
			} else {
				wr("550 5.1.1 <" + arg + ">: Mailing list unknown\r\n")
			}
		case "MAIL":
			wr("250 2.1.0 Ok\r\n")
		case "RCPT":
			u := strings.ToLower(arg)
			u = strings.TrimPrefix(u, "TO:")
			u = strings.TrimSpace(u)
			u = strings.TrimPrefix(u, "<")
			u = strings.TrimSuffix(u, ">")
			local := strings.SplitN(u, "@", 2)[0]
			if smtpUsers[local] {
				wr("250 2.1.5 Ok\r\n")
			} else {
				wr("550 5.1.1 <" + u + ">: Recipient address rejected: User unknown\r\n")
			}
		case "DATA":
			wr("354 End data with <CR><LF>.<CR><LF>\r\n")
			for {
				dl, err := r.ReadString('\n')
				if err != nil {
					return
				}
				if strings.TrimRight(dl, "\r\n") == "." {
					break
				}
			}
			wr("250 2.0.0 Ok: queued as GLOBEX\r\n")
		case "RSET":
			wr("250 2.0.0 Ok\r\n")
		case "NOOP":
			wr("250 2.0.0 Ok\r\n")
		case "QUIT":
			wr("221 2.0.0 Bye\r\n")
			return
		case "HELP":
			wr("214 2.0.0 Commands: EHLO HELO VRFY EXPN MAIL RCPT DATA RSET NOOP QUIT\r\n")
		default:
			wr("500 5.5.1 Command unrecognized\r\n")
		}
	}
}

func main() {
	smtpServer()
}