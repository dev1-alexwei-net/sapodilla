// Package state tracks per-model last-seen timestamps.
package state

import (
	"sync"
	"time"
)

// Store is a concurrency-safe, in-memory last-seen tracker keyed by model name.
type Store struct {
	mu       sync.RWMutex
	lastSeen map[string]time.Time
}

// New returns an empty Store.
func New() *Store {
	return &Store{lastSeen: make(map[string]time.Time)}
}

// Record marks the model as seen at now.
// An empty model key is a no-op (unknown model).
func (s *Store) Record(model string, now time.Time) {
	if model == "" {
		return
	}
	s.mu.Lock()
	s.lastSeen[model] = now
	s.mu.Unlock()
}

// LastSeen returns the most recent recorded time for the model.
// If the model has never been recorded, it returns (zero time, false).
func (s *Store) LastSeen(model string) (time.Time, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	t, ok := s.lastSeen[model]
	return t, ok
}

// Snapshot returns a consistent point-in-time copy of all recorded models.
// The returned map is safe to use without holding the lock.
func (s *Store) Snapshot() map[string]time.Time {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make(map[string]time.Time, len(s.lastSeen))
	for k, v := range s.lastSeen {
		out[k] = v
	}
	return out
}
