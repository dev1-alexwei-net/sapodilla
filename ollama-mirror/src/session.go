package main

import (
	"sync"
	"time"
)

type session struct {
	mu       sync.RWMutex
	total    int64
	lastSeen time.Time
}

type snapshot struct {
	Total    int64 `json:"total"`
	LastSeen *int64 `json:"last_seen"`
}

func (s *session) record(at time.Time) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.total++
	if at.After(s.lastSeen) {
		s.lastSeen = at
	}
}

func (s *session) snapshot() snapshot {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := snapshot{Total: s.total}
	if !s.lastSeen.IsZero() {
		lastSeen := s.lastSeen.UnixMilli()
		result.LastSeen = &lastSeen
	}
	return result
}
