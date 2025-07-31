package powertable

import (
	"fmt"
	"github.com/go-fuego/fuego"
)

func Somelibrary() {
	fmt.Println("hey i'm from powertable")

	s := fuego.NewServer()

	fuego.Get(s, "/", helloWorld)
	s.Run()
}

func helloWorld(c fuego.ContextNoBody) (string, error) {
	return "Hello, World!", nil
}
