// Command sidecar is a lightweight usage-tracking sidecar for a generic
// web API proxy. It receives metadata-only requests from NGINX (via the
// mirror directive) and records a cumulative request count plus the
// timestamp of the most recent request. It exposes a minimal REST API for
// querying usage state.
//
// Design constraints:
//   - stdlib only (no third-party dependencies)
//   - single binary, no persistence
//   - concurrency-safe
//   - generic: works in front of any web API, not just Ollama
package main

import (
	"encoding/json"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/dev1-alexwei-net/ollama-mirror/internal/api"
	"github.com/dev1-alexwei-net/ollama-mirror/internal/state"
	"github.com/dev1-alexwei-net/ollama-mirror/internal/track"
)

func main() {
	addr := flag.String("addr", envOr("ADDR", ":9090"), "listen address for the sidecar API")
	flag.Parse()

	st := &state.Store{}

	// Log every request
	srv := &http.Server{
		Addr:              *addr,
		Handler:           newServer(st),
		ReadHeaderTimeout: 5 * time.Second,
	}

	// Graceful shutdown
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		sig := <-sigCh
		log.Printf("received signal %v, shutting down", sig)
		if err := srv.Close(); err != nil {
			log.Printf("server close: %v", err)
		}
		os.Exit(0)
	}()

	log.Printf("sidecar listening on %s", *addr)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server: %v", err)
	}
}

type server struct{ mux *http.ServeMux }

func newServer(store *state.Store) *server {
	s := &server{mux: http.NewServeMux()}
	s.mux.HandleFunc("/api/healthz", s.healthz)
	s.mux.Handle("/track", track.NewHandler(store))
	s.mux.Handle("/api/usage", api.NewUsageHandler(store))
	return s
}

func (s *server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	log.Printf("%s %s", r.Method, r.URL.Path)
	s.mux.ServeHTTP(w, r)
}

func (s *server) healthz(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{
		"status": "ok",
		"time":   time.Now().UTC().Format(time.RFC3339),
	})
}

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
