.PHONY: all build-core clean

all: build-core

build-core:
	cd plugins/core && go build -o ../../bin/core

clean:
	rm -rf bin/
