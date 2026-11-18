package main

import (
	"context"
	"encoding/json"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func (s *session) track(w http.ResponseWriter, _ *http.Request) {
	s.record(time.Now())
	writeJSON(w, map[string]bool{"ok": true})
}

func (s *session) usage(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.Header().Set("Allow", http.MethodGet)
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	writeJSON(w, s.snapshot())
}

func (s *session) healthz(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, map[string]string{"status": "ok", "time": time.Now().UTC().Format(time.RFC3339)})
}

func writeJSON(w http.ResponseWriter, value any) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(value)
}

func logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s", r.Method, r.URL.Path)
		next.ServeHTTP(w, r)
	})
}

func main() {
	addr := flag.String("addr", envOr("ADDR", ":9090"), "listen address")
	flag.Parse()

	s := &session{lastSeen: time.Now()}
	mux := http.NewServeMux()
	mux.HandleFunc("/track", s.track)
	mux.HandleFunc("/api/usage", s.usage)
	mux.HandleFunc("/api/healthz", s.healthz)
	srv := &http.Server{Addr: *addr, Handler: logRequests(mux), ReadHeaderTimeout: 5 * time.Second}

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-stop
		_ = srv.Shutdown(context.Background())
	}()
	log.Printf("usage API listening on %s", *addr)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}

func envOr(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
