#include <libg15render.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

/* Exact port of libg15's dumpPixmapIntoLCDFormat(): converts libg15render's
   row-major MSB-first bitmap into the LCD's vertical "page" wire format. */
static void dump_to_lcd_format(unsigned char *lcd_buffer, unsigned char const *data) {
    unsigned int output_offset = 32;
    unsigned int base_offset = 0;
    unsigned int curr_row, curr_col;

    for (curr_row = 0; curr_row < 6; ++curr_row) {
        for (curr_col = 0; curr_col < 160; ++curr_col) {
            unsigned int bit = curr_col % 8;
            lcd_buffer[output_offset] =
                (((data[base_offset]        << bit) & 0x80) >> 7) |
                (((data[base_offset + 20]   << bit) & 0x80) >> 6) |
                (((data[base_offset + 40]   << bit) & 0x80) >> 5) |
                (((data[base_offset + 60]   << bit) & 0x80) >> 4) |
                (((data[base_offset + 80]   << bit) & 0x80) >> 3) |
                (((data[base_offset + 100]  << bit) & 0x80) >> 2) |
                (((data[base_offset + 120]  << bit) & 0x80) >> 1) |
                (((data[base_offset + 140]  << bit) & 0x80) >> 0);
            ++output_offset;
            if (bit == 7) base_offset++;
        }
        base_offset += 160 - 20;
    }
}

static void send_frame(g15canvas *canvas) {
    unsigned char report[992];
    memset(report, 0, 32);
    report[0] = 0x03;
    dump_to_lcd_format(report, canvas->buffer);

    /* Stable symlink from the udev rule (99-g510-lcd.rules) -- the raw
       hidraw number can shift across reboots/replugs, this doesn't. */
    FILE *f = fopen("/dev/g510-lcd", "wb");
    if (!f) { perror("open /dev/g510-lcd"); return; }
    fwrite(report, 1, 992, f);
    fclose(f);
}

/* --- stat readers --- */

static void read_cpu_totals(unsigned long long *idle, unsigned long long *total) {
    FILE *f = fopen("/proc/stat", "r");
    unsigned long long user, nice, sys, idl, iowait, irq, softirq, steal;
    fscanf(f, "cpu %llu %llu %llu %llu %llu %llu %llu %llu",
           &user, &nice, &sys, &idl, &iowait, &irq, &softirq, &steal);
    fclose(f);
    *idle = idl + iowait;
    *total = user + nice + sys + idl + iowait + irq + softirq + steal;
}

static double get_cpu_percent(void) {
    static unsigned long long prev_idle = 0, prev_total = 0;
    unsigned long long idle, total;
    read_cpu_totals(&idle, &total);
    unsigned long long dt = total - prev_total;
    unsigned long long di = idle - prev_idle;
    double pct = (dt > 0) ? (100.0 * (double)(dt - di) / (double)dt) : 0.0;
    prev_idle = idle; prev_total = total;
    return pct;
}

/* returns used/total RAM in KB via MemTotal/MemAvailable */
static void get_ram_kb(long *used_kb, long *total_kb) {
    FILE *f = fopen("/proc/meminfo", "r");
    char label[64];
    long value;
    long mem_total = 0, mem_avail = 0;
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "%63s %ld", label, &value) == 2) {
            if (strcmp(label, "MemTotal:") == 0) mem_total = value;
            else if (strcmp(label, "MemAvailable:") == 0) mem_avail = value;
        }
    }
    fclose(f);
    *total_kb = mem_total;
    *used_kb = mem_total - mem_avail;
}

static int get_cpu_temp_c(void) {
    FILE *f = fopen("/sys/class/hwmon/hwmon3/temp1_input", "r");
    if (!f) return -1;
    int millideg = 0;
    fscanf(f, "%d", &millideg);
    fclose(f);
    return millideg / 1000;
}

static void get_vram_bytes(unsigned long long *used, unsigned long long *total) {
    FILE *f;
    *used = 0; *total = 0;
    f = fopen("/sys/class/drm/card1/device/mem_info_vram_used", "r");
    if (f) { fscanf(f, "%llu", used); fclose(f); }
    f = fopen("/sys/class/drm/card1/device/mem_info_vram_total", "r");
    if (f) { fscanf(f, "%llu", total); fclose(f); }
}

static void format_gb(unsigned long long bytes, char *out, size_t outlen) {
    snprintf(out, outlen, "%.1fG", bytes / (1024.0 * 1024.0 * 1024.0));
}

static double get_cpu_ghz(void) {
    FILE *f = fopen("/proc/cpuinfo", "r");
    if (!f) return 0.0;
    char line[256];
    double mhz = 0.0;
    while (fgets(line, sizeof(line), f)) {
        if (strncmp(line, "cpu MHz", 7) == 0) {
            sscanf(strchr(line, ':') + 1, "%lf", &mhz);
            break;
        }
    }
    fclose(f);
    return mhz / 1000.0;
}

/* --- layout --- */

#define ROW_CPU  3
#define ROW_RAM  33
#define ROW_VRAM 23
#define ROW_TEMP 13
#define BAR_H    4

#define LABEL_X  6
#define PCT_X    35
#define BAR_X1   62
#define BAR_X2   122
#define AMT_X    125

/* Slim, borderless bar: a 1px baseline marks full scale, a filled block
   on top shows the current value. No boxed outline (elegant, not "fat"). */
static void draw_slim_bar(g15canvas *c, int x1, int x2, int y, int h, int pct) {
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    g15r_drawLine(c, x1, y + h + 1, x2, y + h + 1, G15_COLOR_BLACK);
    int fill_x2 = x1 + (int)((x2 - x1) * (pct / 100.0));
    if (fill_x2 > x1) {
        g15r_pixelBox(c, x1, y, fill_x2, y + h, G15_COLOR_BLACK, 1, G15_PIXEL_FILL);
    }
}

/* Labels: Eurostile Bold (custom-converted, matches original G510 look).
   Numbers: the library's own built-in bitmap font -- it was purpose-built
   for this exact tiny resolution, so it stays legible where converted
   TTFs keep garbling at 6-8px. */
static g15font *label_font = NULL;

#define LABEL_Y_OFFSET 3 /* Eurostile's metrics sit higher than the number font's */

static void draw_row(g15canvas *c, int y, const char *label, int pct,
                      const char *pct_str, const char *amount, int pct_y_nudge) {
    g15r_G15FontRenderString(c, label_font, (char*)label, 0, LABEL_X, y + LABEL_Y_OFFSET, G15_COLOR_BLACK, 0);
    g15r_renderString(c, (unsigned char*)pct_str, 0, G15_TEXT_SMALL, PCT_X, y + pct_y_nudge);
    draw_slim_bar(c, BAR_X1, BAR_X2, y, BAR_H, pct);
    if (amount) {
        g15r_renderString(c, (unsigned char*)amount, 0, G15_TEXT_SMALL, AMT_X, y);
    }
}

static const char *screen_state_path(void) {
    static char path[256];
    const char *runtime = getenv("XDG_RUNTIME_DIR");
    snprintf(path, sizeof(path), "%s/g510lcd_screen", runtime ? runtime : "/tmp");
    return path;
}

static int read_screen(void) {
    FILE *f = fopen(screen_state_path(), "r");
    if (!f) return 0;
    int s = 0;
    fscanf(f, "%d", &s);
    fclose(f);
    return s;
}

/* Screen 1: a simple large clock. New screens go here -- L1 cycles
   through however many screens NUM_SCREENS (in g510_lcd_buttons.c)
   currently accounts for. */
static void draw_clock_screen(g15canvas *c) {
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    char time_str[16], date_str[32];
    strftime(time_str, sizeof(time_str), "%H:%M:%S", t);
    strftime(date_str, sizeof(date_str), "%A, %d %B", t);

    g15r_G15FPrint(c, time_str, 20, 8, G15_TEXT_LARGE, G15_JUSTIFY_LEFT, G15_COLOR_BLACK, 0);
    g15r_renderString(c, (unsigned char*)date_str, 0, G15_TEXT_SMALL, 10, 30);
}

/* Screens 2-5: temporary test screens for the L2-L5 buttons, so presses
   are visibly confirmed before real actions get programmed onto them. */
static void draw_button_test_screen(g15canvas *c, int screen) {
    char label[8];
    snprintf(label, sizeof(label), "L%d", screen);
    g15r_G15FPrint(c, label, 0, 12, G15_TEXT_HUGE, G15_JUSTIFY_CENTER, G15_COLOR_BLACK, 0);
}

int main(void) {
    int max_temp_seen = 0; /* highest temp observed since this program started */
    label_font = g15r_loadG15Font("/home/alextria/Desktop/System-Fixes/G510LCD/fonts/lcd-label-8.fnt");
    if (!label_font) { fprintf(stderr, "failed to load custom font\n"); return 1; }
    while (1) {
        g15canvas canvas;
        g15r_initCanvas(&canvas);

        int screen = read_screen();
        if (screen == 1) {
            draw_clock_screen(&canvas);
            send_frame(&canvas);
            sleep(1);
            continue;
        }
        if (screen >= 2 && screen <= 5) {
            draw_button_test_screen(&canvas, screen);
            send_frame(&canvas);
            sleep(1);
            continue;
        }

        double cpu_pct = get_cpu_percent();
        char cpu_str[16], cpu_ghz_str[16];
        snprintf(cpu_str, sizeof(cpu_str), "%3d%%", (int)(cpu_pct + 0.5));
        snprintf(cpu_ghz_str, sizeof(cpu_ghz_str), "%.1fGHz", get_cpu_ghz());
        draw_row(&canvas, ROW_CPU, "CPU", (int)cpu_pct, cpu_str, cpu_ghz_str, 0);

        long ram_used_kb, ram_total_kb;
        get_ram_kb(&ram_used_kb, &ram_total_kb);
        int ram_pct = ram_total_kb > 0 ? (int)(100.0 * ram_used_kb / ram_total_kb) : 0;
        char ram_pct_str[16], ram_amt_str[16];
        snprintf(ram_pct_str, sizeof(ram_pct_str), "%3d%%", ram_pct);
        snprintf(ram_amt_str, sizeof(ram_amt_str), "%.1fG", ram_used_kb / (1024.0 * 1024.0));
        draw_row(&canvas, ROW_RAM, "RAM", ram_pct, ram_pct_str, ram_amt_str, 0);

        unsigned long long vram_used, vram_total;
        get_vram_bytes(&vram_used, &vram_total);
        int vram_pct = vram_total > 0 ? (int)(100.0 * vram_used / vram_total) : 0;
        char vram_pct_str[16], vram_amt_str[16];
        snprintf(vram_pct_str, sizeof(vram_pct_str), "%3d%%", vram_pct);
        format_gb(vram_used, vram_amt_str, sizeof(vram_amt_str));
        draw_row(&canvas, ROW_VRAM, "VRAM", vram_pct, vram_pct_str, vram_amt_str, 0);

        int temp_c = get_cpu_temp_c();
        if (temp_c > max_temp_seen) max_temp_seen = temp_c;
        char temp_str[16], temp_max_str[16];
        snprintf(temp_str, sizeof(temp_str), "%d" "\xB0" "C", temp_c);
        snprintf(temp_max_str, sizeof(temp_max_str), "MAX %d" "\xB0" "C", max_temp_seen);
        /* temp bar: use % of a 0-90C scale just to give a visual sense of magnitude */
        int temp_pct = temp_c > 0 ? (temp_c * 100 / 90) : 0;
        draw_row(&canvas, ROW_TEMP, "TEMP", temp_pct, temp_str, temp_max_str, 1);

        send_frame(&canvas);
        sleep(2);
    }
    return 0;
}
