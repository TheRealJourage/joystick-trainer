# Build on the Pi: needs piolib (https://github.com/raspberrypi/utils, piolib/) installed.
ppm_pio: ppm_pio.c
	$(CC) -O2 -Wall -Wextra -o $@ $< -lpio

ppm_pio_dump: ppm_pio.c
	$(CC) -O2 -Wall -Wextra -DDUMP_ONLY -o $@ $<

clean:
	rm -f ppm_pio ppm_pio_dump
