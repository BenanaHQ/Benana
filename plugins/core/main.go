package main

import (
	"encoding/json"
	"fmt"
	"os"
	"sync"

	"github.com/go-fuego/fuego"
)

type Plugin struct {
	ID          string `json:"ID"`
	Name        string `json:"Name"`
	Description string `json:"Description"`
	Version     string `json:"Version"`
	Author      string `json:"Author"`
	Type        string `json:"Type"`
}

type Plugins struct {
	data sync.Map
}

func (p *Plugins) Add(plugin Plugin) {
	p.data.Store(plugin.ID, plugin)
}

func (p *Plugins) Delete(id string) {
	p.data.Delete(id)
}

func (p *Plugins) Update(id string, plugin Plugin) {
	p.data.Store(id, plugin)
}

func (p *Plugins) GetByName(name string) (*Plugin, error) {
	var result *Plugin
	found := false

	p.data.Range(func(_, value any) bool {
		plugin, ok := value.(Plugin)
		if !ok {
			return true
		}
		if plugin.Name == name {
			result = &plugin
			found = true
			return false
		}
		return true
	})

	if !found {
		return nil, fmt.Errorf("plugin with name %q not found", name)
	}
	return result, nil
}

func (p *Plugins) GetByID(id string) (*Plugin, error) {
	value, ok := p.data.Load(id)
	if !ok {
		return nil, fmt.Errorf("plugin with ID %q not found", id)
	}
	plugin, ok := value.(Plugin)
	if !ok {
		return nil, fmt.Errorf("failed to convert value to Plugin")
	}
	return &plugin, nil
}

func (p *Plugins) GetAll() ([]Plugin, error) {
	var all []Plugin
	p.data.Range(func(_, value any) bool {
		plugin, ok := value.(Plugin)
		if ok {
			all = append(all, plugin)
		}
		return true
	})
	return all, nil
}

func LoadPluginsFromFile(path string) (*Plugins, error) {
	file, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var raw []Plugin
	if err := json.Unmarshal(file, &raw); err != nil {
		return nil, err
	}

	p := &Plugins{}
	for _, plugin := range raw {
		p.Add(plugin)
	}
	return p, nil
}

// NewPluginListResponse creates a new successful plugin list response
func NewPluginListResponse(status int, message string, data *[]Plugin) *PluginListResponse {
	return &PluginListResponse{
		Success: true,
		Status:  status,
		Message: message,
		Data:    data,
	}
}

// PluginListResponse is a concrete type for plugin list responses
type PluginListResponse struct {
	Success    bool           `json:"success"`
	Status     int            `json:"status"`
	Message    string         `json:"message"`
	Data       *[]Plugin      `json:"data"`
	Errors     []APIError     `json:"errors,omitempty"`
	Meta       *APIMeta       `json:"meta,omitempty"`
	Pagination *APIPagination `json:"pagination,omitempty"`
	Warnings   []APIWarning   `json:"warnings,omitempty"`
}

// NewPluginListErrorResponse creates a new error plugin list response
func NewPluginListErrorResponse(status int, message string, errors []APIError) *PluginListResponse {
	return &PluginListResponse{
		Success: false,
		Status:  status,
		Message: message,
		Data:    nil,
		Errors:  errors,
	}
}

func main() {
	s := fuego.NewServer()
	fuego.Get(s, "/plugins", getPlugins)
	s.Run()
}

func getPlugins(c fuego.ContextNoBody) (*PluginListResponse, error) {
	plugins, err := LoadPluginsFromFile("./plugins.json")
	if err != nil {
		return NewPluginListErrorResponse(500, "Failed to retrieve plugins", []APIError{
			{Code: "INTERNAL_ERROR", Message: err.Error()},
		}), nil
	}

	allPlugins, err := plugins.GetAll()
	if err != nil {
		errorResponse := NewPluginListErrorResponse(500, "Failed to retrieve plugins", []APIError{
			{Code: "INTERNAL_ERROR", Message: err.Error()},
		})
		return errorResponse, nil
	}

	response := NewPluginListResponse(200, "Plugins retrieved successfully", &allPlugins)
	return response, nil
}
