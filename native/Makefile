# Build on the Pi: needs piolib (https://github.com/raspberrypi/utils, piolib/) installed.
# PIOLIB=<prefix> builds against a piolib installed under that prefix instead of /usr/local
# (scripts/setup-pi.sh uses the repo-local .piolib/).
ifdef PIOLIB
PIO_FLAGS = -I$(PIOLIB)/include -I$(PIOLIB)/include/piolib -L$(PIOLIB)/lib -Wl,-rpath,$(PIOLIB)/lib
endif

ppm_pio: ppm_pio.c
	$(CC) -O2 -Wall -Wextra $(PIO_FLAGS) -o $@ $< -lpio

ppm_pio_dump: ppm_pio.c
	$(CC) -O2 -Wall -Wextra -DDUMP_ONLY -o $@ $<

clean:
	rm -f ppm_pio ppm_pio_dump
