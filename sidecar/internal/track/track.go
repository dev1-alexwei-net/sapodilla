// Package track handles the sidecar's /track endpoint.
//
// It is intentionally generic: it accepts any request (any method, any path,
// any body) and simply registers that a request happened. It does not parse
// the body, the URL, or any headers.
package track

import (
	"encoding/json"
	"log"
	"net/http"
	"time"

	"github.com/dev1-alexwei-net/ollama-mirror/internal/state"
)

// Handler serves POST /track.
type Handler struct {
	Store *state.Store
	Now   func() time.Time // injectable for tests
}

// NewHandler returns a track Handler with the given store.
func NewHandler(s *state.Store) *Handler {
	return &Handler{Store: s, Now: time.Now}
}

// ServeHTTP handles the /track request.
//
// The body is ignored: the sidecar only needs to know that a request
// occurred. NGINX mirrors requests here (with mirror_request_body off),
// so the body is typically empty.
func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	now := h.Now()
	h.Store.Record(now)

	// Always 200, minimal body. NGINX mirror does not use our response.
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]any{"ok": true})
}

// LogMiddleware logs every request at debug level.
func LogMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("track: %s %s", r.Method, r.URL.Path)
		next.ServeHTTP(w, r)
	})
}
