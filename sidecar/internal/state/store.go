// Package state tracks the total and last-seen time of proxied requests.
package state

import (
	"sync"
	"time"
)

// Snapshot is an atomic view of the tracked request usage.
type Snapshot struct {
	Total    int64      `json:"total"`
	LastSeen *time.Time `json:"last_seen"`
}

// Store is a concurrency-safe in-memory counter. Its zero value is ready to use.
type Store struct {
	mu       sync.RWMutex
	total    int64
	lastSeen time.Time
}

func (s *Store) Record(at time.Time) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.total++
	if at.After(s.lastSeen) {
		s.lastSeen = at
	}
}

// Snapshot returns the current usage without exposing the store's internal lock.
func (s *Store) Snapshot() Snapshot {
	s.mu.RLock()
	defer s.mu.RUnlock()
	snapshot := Snapshot{Total: s.total}
	if !s.lastSeen.IsZero() {
		lastSeen := s.lastSeen
		snapshot.LastSeen = &lastSeen
	}
	return snapshot
}
