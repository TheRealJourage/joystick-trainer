/*
 * PPM generator on the Raspberry Pi 5 RP1 PIO (piolib).
 *
 * Reads lines on stdin: "<us> <us> ... <us>" sets the channels and starts frames,
 * "stop" ends frame output (pin rests at idle), "quit" or EOF exits.
 *
 * PIO program: one 32-bit word per edge. Bit 0 = pin level, bits 1..31 = ticks - 4.
 * pull + out pins + out x + (x+1) x jmp = ticks - 4 + 4 cycles, so ticks = word duration.
 */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <poll.h>
#include <unistd.h>

#ifndef DUMP_ONLY
#include "hardware/pio.h"
#include "pico/stdlib.h"
#endif

#define MAX_CHANNELS 16
#define TICKS_PER_US 10
#define PROGRAM_OVERHEAD_TICKS 4

static int gpio_pin = 18;
static int channel_count = 8;
static int pulse_us = 300;
static int frame_us = 22500;
static int active_high = 1;
static double pio_hz = 200e6;

static uint32_t edge_word(int level, int duration_us)
{
    return ((uint32_t)(duration_us * TICKS_PER_US - PROGRAM_OVERHEAD_TICKS) << 1) | (level ? 1u : 0u);
}

static int build_frame(const int *channels, uint32_t *words)
{
    int high = active_high ? 1 : 0, low = !high, used = 0, n = 0;
    for (int i = 0; i < channel_count; i++) {
        int w = channels[i] < 1000 ? 1000 : channels[i] > 2000 ? 2000 : channels[i];
        used += w;
        words[n++] = edge_word(high, pulse_us);
        words[n++] = edge_word(low, w - pulse_us);
    }
    words[n++] = edge_word(high, pulse_us);
    words[n++] = edge_word(low, frame_us - used - pulse_us);
    return n;
}

#ifndef DUMP_ONLY
static PIO pio;
static int sm;

static void pio_start(void)
{
    uint16_t instructions[] = {
        pio_encode_pull(false, true),
        pio_encode_out(pio_pins, 1),
        pio_encode_out(pio_x, 31),
        pio_encode_jmp_x_dec(3),
    };
    static pio_program_t program;
    program.instructions = instructions;
    program.length = 4;
    program.origin = -1;

    pio = pio0;
    sm = pio_claim_unused_sm(pio, true);
    uint offset = pio_add_program(pio, &program);
    pio_gpio_init(pio, gpio_pin);
    pio_sm_set_consecutive_pindirs(pio, sm, gpio_pin, 1, true);
    pio_sm_config c = pio_get_default_sm_config();
    sm_config_set_wrap(&c, offset, offset + 3);
    sm_config_set_out_pins(&c, gpio_pin, 1);
    sm_config_set_out_shift(&c, true, false, 32);
    sm_config_set_clkdiv(&c, (float)(pio_hz / (TICKS_PER_US * 1e6)));
    pio_sm_init(pio, sm, offset, &c);
    pio_sm_put_blocking(pio, sm, edge_word(!active_high, 1000));
    pio_sm_set_enabled(pio, sm, true);
}

static void send_frame(const uint32_t *words, int n)
{
    for (int i = 0; i < n; i++)
        pio_sm_put_blocking(pio, sm, words[i]);
}
#endif

static void usage(void)
{
    fprintf(stderr,
            "usage: ppm_pio [--gpio N] [--channels N] [--pulse-us N] [--frame-us N]\n"
            "               [--active-low] [--pio-hz HZ] [--dump us...]\n");
    exit(2);
}

int main(int argc, char **argv)
{
    int dump = 0, dump_channels[MAX_CHANNELS];
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--gpio") && i + 1 < argc) gpio_pin = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--channels") && i + 1 < argc) channel_count = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--pulse-us") && i + 1 < argc) pulse_us = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--frame-us") && i + 1 < argc) frame_us = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--pio-hz") && i + 1 < argc) pio_hz = atof(argv[++i]);
        else if (!strcmp(argv[i], "--active-low")) active_high = 0;
        else if (!strcmp(argv[i], "--dump")) {
            dump = 1;
            for (int k = 0; k < channel_count && i + 1 < argc; k++) dump_channels[k] = atoi(argv[++i]);
        } else usage();
    }
    if (channel_count < 1 || channel_count > MAX_CHANNELS) usage();

    uint32_t words[2 * MAX_CHANNELS + 2];
    if (dump) {
        int n = build_frame(dump_channels, words);
        for (int i = 0; i < n; i++)
            printf("%u %u\n", words[i] & 1, (((words[i] >> 1) + PROGRAM_OVERHEAD_TICKS)) / TICKS_PER_US);
        return 0;
    }

#ifdef DUMP_ONLY
    fprintf(stderr, "built with DUMP_ONLY\n");
    return 2;
#else
    pio_start();

    int channels[MAX_CHANNELS];
    for (int i = 0; i < channel_count; i++) channels[i] = 1500;
    int running = 0;
    char buf[512];
    size_t len = 0;
    for (;;) {
        struct pollfd input = {.fd = STDIN_FILENO, .events = POLLIN};
        if (!running || poll(&input, 1, 0) > 0) {
            if (len >= sizeof buf - 1) len = 0;
            ssize_t got = read(STDIN_FILENO, buf + len, sizeof buf - len - 1);
            if (got == 0) break;
            if (got < 0) { if (errno == EINTR) continue; break; }
            len += (size_t)got;
        }
        buf[len] = 0;
        char *newline;
        while ((newline = strchr(buf, '\n')) != NULL) {
            *newline = 0;
            if (!strcmp(buf, "quit")) return 0;
            if (!strcmp(buf, "stop")) running = 0;
            else {
                char *cursor = buf;
                for (int i = 0; i < channel_count; i++) {
                    char *end;
                    long v = strtol(cursor, &end, 10);
                    if (end == cursor) break;
                    channels[i] = (int)v;
                    cursor = end;
                }
                running = 1;
            }
            len -= (size_t)(newline + 1 - buf);
            memmove(buf, newline + 1, len + 1);
        }
        if (running) {
            int n = build_frame(channels, words);
            send_frame(words, n);
        }
    }
    return 0;
#endif
}
