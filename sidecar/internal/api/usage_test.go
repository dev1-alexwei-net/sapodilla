// Package api provides the read-only REST API for querying usage state.
package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/dev1-alexwei-net/ollama-mirror/internal/state"
)

func newTestServer(t *testing.T) (*state.Store, *httptest.Server) {
	t.Helper()
	store := state.New()
	srv := httptest.NewServer(NewUsageHandler(store))
	t.Cleanup(srv.Close)
	return store, srv
}

func TestUsageJSONShape(t *testing.T) {
	store, srv := newTestServer(t)

	// Empty state: total=0, last_seen=null
	body := doGet(t, srv.URL+"/api/usage")
	var resp struct {
		Total    int64   `json:"total"`
		LastSeen *string `json:"last_seen"`
	}
	if err := json.Unmarshal(body, &resp); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if resp.Total != 0 {
		t.Fatalf("total = %d, want 0", resp.Total)
	}
	if resp.LastSeen != nil {
		t.Fatalf("last_seen = %v, want null", *resp.LastSeen)
	}

	// After a record: total=1, last_seen is a string
	now := time.Now().UTC()
	store.Record(now)
	body = doGet(t, srv.URL+"/api/usage")
	if err := json.Unmarshal(body, &resp); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if resp.Total != 1 {
		t.Fatalf("total = %d, want 1", resp.Total)
	}
	if resp.LastSeen == nil {
		t.Fatal("last_seen = null, want a timestamp string")
	}
}

func TestUsageAfterMultipleRecords(t *testing.T) {
	store, srv := newTestServer(t)
	base := time.Now().UTC()
	for i := 0; i < 5; i++ {
		store.Record(base.Add(time.Duration(i) * time.Second))
	}
	body := doGet(t, srv.URL+"/api/usage")
	var resp struct {
		Total    int64   `json:"total"`
		LastSeen *string `json:"last_seen"`
	}
	if err := json.Unmarshal(body, &resp); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if resp.Total != 5 {
		t.Fatalf("total = %d, want 5", resp.Total)
	}
	if resp.LastSeen == nil {
		t.Fatal("last_seen = null, want timestamp")
	}
}

func TestUsageMethodNotAllowed(t *testing.T) {
	_, srv := newTestServer(t)
	req, _ := http.NewRequest(http.MethodPost, srv.URL+"/api/usage", nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Fatalf("status = %d, want 405", resp.StatusCode)
	}
}

func doGet(t *testing.T, url string) []byte {
	t.Helper()
	resp, err := http.Get(url)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want 200", resp.StatusCode)
	}
	var buf bytes.Buffer
	if _, err := buf.ReadFrom(resp.Body); err != nil {
		t.Fatal(err)
	}
	return buf.Bytes()
}
