package main

import "time"

type APIError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Field   string `json:"field,omitempty"`
}

type APIWarning struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

type APIMeta struct {
	Timestamp *time.Time `json:"timestamp,omitempty"`
	RequestID *string    `json:"requestId,omitempty"`
	Version   *string    `json:"version,omitempty"`
}

type APIPagination struct {
	Page       int  `json:"page"`
	Limit      int  `json:"limit"`
	Total      int  `json:"total"`
	TotalPages int  `json:"totalPages"`
	HasNext    bool `json:"hasNext"`
	HasPrev    bool `json:"hasPrev"`
}

type APIResponse[T any] struct {
	Success    bool           `json:"success"`
	Status     int            `json:"status"`
	Message    string         `json:"message"`
	Data       *T             `json:"data"`
	Errors     []APIError     `json:"errors,omitempty"`
	Meta       *APIMeta       `json:"meta,omitempty"`
	Pagination *APIPagination `json:"pagination,omitempty"`
	Warnings   []APIWarning   `json:"warnings,omitempty"`
}

func NewAPIResponse[T any](status int, message string, data *T) *APIResponse[T] {
	return &APIResponse[T]{
		Success: true,
		Status:  status,
		Message: message,
		Data:    data,
	}
}

func NewAPIErrorResponse[T any](status int, message string, errors []APIError) *APIResponse[T] {
	return &APIResponse[T]{
		Success: false,
		Status:  status,
		Message: message,
		Data:    nil,
		Errors:  errors,
	}
}

func (r *APIResponse[T]) WithMeta(meta *APIMeta) *APIResponse[T] {
	r.Meta = meta
	return r
}

func (r *APIResponse[T]) WithPagination(pagination *APIPagination) *APIResponse[T] {
	r.Pagination = pagination
	return r
}

func (r *APIResponse[T]) WithWarnings(warnings []APIWarning) *APIResponse[T] {
	r.Warnings = warnings
	return r
}