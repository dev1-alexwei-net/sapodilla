// Package api exposes the sidecar's usage snapshot.
package api

import (
	"encoding/json"
	"net/http"

	"github.com/dev1-alexwei-net/ollama-mirror/internal/state"
)

// UsageReader is the read behavior required by UsageHandler.
type UsageReader interface {
	Snapshot() state.Snapshot
}

// UsageHandler serves the current usage snapshot.
type UsageHandler struct {
	store UsageReader
}

// NewUsageHandler constructs a UsageHandler using the given reader.
func NewUsageHandler(store UsageReader) *UsageHandler {
	return &UsageHandler{store: store}
}

func (h *UsageHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.Header().Set("Allow", http.MethodGet)
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(h.store.Snapshot())
}
