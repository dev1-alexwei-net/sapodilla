// Package api provides the read-only REST API for querying usage state.
package api

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/dev1-alexwei-net/ollama-mirror/internal/state"
)

// UsageResponse is the shape of GET /api/usage.
//
// It is intentionally minimal: just the cumulative request count and the
// timestamp of the most recent request. No per-model, per-endpoint, or
// per-client state is exposed.
type UsageResponse struct {
	Total    int64      `json:"total"`
	LastSeen *time.Time `json:"last_seen"`
}

// UsageHandler serves GET /api/usage.
type UsageHandler struct {
	Store *state.Store
}

// NewUsageHandler returns a handler with the given store.
func NewUsageHandler(s *state.Store) *UsageHandler {
	return &UsageHandler{Store: s}
}

// ServeHTTP handles GET /api/usage.
func (h *UsageHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.Header().Set("Allow", "GET")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	total := h.Store.Total()
	lastSeen := h.Store.LastSeen()

	resp := UsageResponse{
		Total:    total,
		LastSeen: nil,
	}
	if !lastSeen.IsZero() {
		ts := lastSeen
		resp.LastSeen = &ts
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(resp)
}
