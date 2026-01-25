CC = clang
CFLAGS = -Wall -g
LDFLAGS = -lutil

all: shell

shell: shell.o
	$(CC) $(LDFLAGS) -o $@ $^

clean:
	rm -f shell *.o
