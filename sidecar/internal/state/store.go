// Package state tracks usage for a generic web API proxy.
//
// It records only two things:
//   - total: cumulative request count
//   - lastSeen: timestamp of the most recent request
//
// No endpoint, model, or per-client state is kept.
package state

import (
	"sync"
	"time"
)

// Store is a concurrency-safe, in-memory usage counter.
type Store struct {
	mu       sync.RWMutex
	total    int64
	lastSeen time.Time
}

// New returns an empty Store.
func New() *Store {
	return &Store{}
}

// Record registers one request that occurred at now.
// It increments the total count and updates lastSeen to the most recent time.
func (s *Store) Record(now time.Time) {
	s.mu.Lock()
	s.total++
	if now.After(s.lastSeen) {
		s.lastSeen = now
	}
	s.mu.Unlock()
}

// Total returns the cumulative request count.
func (s *Store) Total() int64 {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.total
}

// LastSeen returns the most recent recorded timestamp.
// If no request has been recorded, it returns the zero time.
func (s *Store) LastSeen() time.Time {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.lastSeen
}
