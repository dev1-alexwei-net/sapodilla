package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/dev1-alexwei-net/ollama-mirror/internal/state"
)

func TestUsageEmpty(t *testing.T) {
	s := state.New()
	h := NewUsageHandler(s)

	req := httptest.NewRequest("GET", "/api/usage", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	var resp UsageResponse
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if resp.Total != 0 {
		t.Fatalf("total = %d, want 0", resp.Total)
	}
	if len(resp.Models) != 0 {
		t.Fatalf("models = %v, want empty", resp.Models)
	}
}

func TestUsagePopulated(t *testing.T) {
	s := state.New()
	now := time.Date(2026, 11, 15, 12, 0, 0, 0, time.UTC)
	s.Record("llama3.1:8b", now)
	s.Record("mistral:7b", now.Add(-1*time.Hour))

	h := NewUsageHandler(s)
	req := httptest.NewRequest("GET", "/api/usage", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	var resp UsageResponse
	json.NewDecoder(rec.Body).Decode(&resp)

	if resp.Total != 2 {
		t.Fatalf("total = %d, want 2", resp.Total)
	}
	if !resp.LastSeen.Equal(now) {
		t.Fatalf("lastSeen = %v, want %v", resp.LastSeen, now)
	}
	if _, ok := resp.Models["llama3.1:8b"]; !ok {
		t.Fatal("llama3.1:8b not in models")
	}
	if _, ok := resp.Models["mistral:7b"]; !ok {
		t.Fatal("mistral:7b not in models")
	}
}

func TestUsageMethodNotAllowed(t *testing.T) {
	s := state.New()
	h := NewUsageHandler(s)

	req := httptest.NewRequest("POST", "/api/usage", strings.NewReader("{}"))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("status = %d, want 405", rec.Code)
	}
}

func TestUsageSnapshotStability(t *testing.T) {
	// Record two models, take snapshot, then record a third.
	// The first response must NOT include the third model.
	s := state.New()
	h := NewUsageHandler(s)
	now := time.Now()

	s.Record("a", now)
	s.Record("b", now)

	req := httptest.NewRequest("GET", "/api/usage", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	// Mutate after the snapshot was served
	s.Record("c", now)

	var resp UsageResponse
	json.NewDecoder(rec.Body).Decode(&resp)

	if _, ok := resp.Models["c"]; ok {
		t.Fatal("snapshot should not contain model c (recorded after response)")
	}
	if resp.Total != 2 {
		t.Fatalf("total = %d, want 2", resp.Total)
	}
}

func TestUsageJSONShape(t *testing.T) {
	s := state.New()
	now := time.Date(2026, 11, 15, 12, 0, 0, 0, time.UTC)
	s.Record("x", now)

	h := NewUsageHandler(s)
	req := httptest.NewRequest("GET", "/api/usage", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	// Verify top-level keys
	var raw map[string]json.RawMessage
	json.NewDecoder(rec.Body).Decode(&raw)

	for _, key := range []string{"models", "last_seen", "total"} {
		if _, ok := raw[key]; !ok {
			t.Fatalf("missing top-level key %q in response", key)
		}
	}
}
