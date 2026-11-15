package track

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/dev1-alexwei-net/ollama-mirror/internal/state"
)

func TestTrackRecordsModelFromBody(t *testing.T) {
	s := state.New()
	h := NewHandler(s)
	fixed := time.Date(2026, 11, 15, 12, 0, 0, 0, time.UTC)
	h.Now = func() time.Time { return fixed }

	body := `{"model":"llama3.1:8b","prompt":"hi"}`
	req := httptest.NewRequest("POST", "/track", strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	got, ok := s.LastSeen("llama3.1:8b")
	if !ok {
		t.Fatal("model not recorded")
	}
	if !got.Equal(fixed) {
		t.Fatalf("lastSeen = %v, want %v", got, fixed)
	}
}

func TestTrackRecordsModelFromQueryParam(t *testing.T) {
	s := state.New()
	h := NewHandler(s)

	req := httptest.NewRequest("GET", "/track?model=mistral:7b", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if _, ok := s.LastSeen("mistral:7b"); !ok {
		t.Fatal("model from query param not recorded")
	}
}

func TestTrackEmptyModelNoop(t *testing.T) {
	s := state.New()
	h := NewHandler(s)

	req := httptest.NewRequest("POST", "/track", strings.NewReader("{}"))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if len(s.Snapshot()) != 0 {
		t.Fatalf("expected no records, got %v", s.Snapshot())
	}
}

func TestTrackMalformedBodyStill200(t *testing.T) {
	s := state.New()
	h := NewHandler(s)

	req := httptest.NewRequest("POST", "/track", strings.NewReader("not json at all"))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 even for malformed body", rec.Code)
	}
}

func TestTrackResponseBodyIsJSON(t *testing.T) {
	s := state.New()
	h := NewHandler(s)

	req := httptest.NewRequest("POST", "/track", strings.NewReader(`{"model":"x"}`))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	var resp map[string]any
	if err := json.NewDecoder(rec.Body).Decode(&resp); err != nil {
		t.Fatalf("response is not valid JSON: %v", err)
	}
	if resp["ok"] != true {
		t.Fatalf("expected ok=true, got %v", resp)
	}
}
