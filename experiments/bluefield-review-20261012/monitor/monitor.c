#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <ctype.h>
#include <dirent.h>
#include <time.h>
#include <unistd.h>
#include <doca_dev.h>
#include <doca_error.h>

/* Test builds override this at compile time; production reads only /sys. */
#ifndef SYSFS_ROOT
#define SYSFS_ROOT "/sys"
#endif
static const char *counters[] = {
    "rx_packets", "tx_packets", "rx_bytes", "tx_bytes", "rx_errors", "tx_errors"
};

static void string_json(const char *s)
{
    if (!s) { fputs("null", stdout); return; }
    putchar('"');
    for (; *s; ++s) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') { putchar('\\'); putchar(c); }
        else if (c < 32 || c >= 127) printf("\\u%04x", c);
        else putchar(c);
    }
    putchar('"');
}

static int component(const char *s)
{
    return s && *s && strcmp(s, ".") && strcmp(s, "..") && !strchr(s, '/');
}

/* An ambiguous mapping is unknown, never the first arbitrary interface. */
static int find_iface(const char *ibdev, char *iface, size_t size)
{
    char path[1024];
    if (!component(ibdev)) return EINVAL;
    int n = snprintf(path, sizeof(path), "%s/class/infiniband/%s/device/net", SYSFS_ROOT, ibdev);
    if (n < 0 || (size_t)n >= sizeof(path)) return ENAMETOOLONG;
    DIR *dir = opendir(path);
    if (!dir) return errno;
    int count = 0, error = 0;
    struct dirent *entry;
    for (;;) {
        errno = 0;
        entry = readdir(dir);
        if (!entry) { if (errno) error = errno; break; }
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        count++;
        if (strlen(entry->d_name) >= size) error = ENAMETOOLONG;
        else memcpy(iface, entry->d_name, strlen(entry->d_name) + 1);
    }
    closedir(dir);
    if (error) return error;
    return count == 1 ? 0 : count == 0 ? ENOENT : EEXIST;
}

static int read_text(const char *iface, const char *field, char *buf, size_t size)
{
    char path[1024];
    if (!component(iface)) return EINVAL;
    int n = snprintf(path, sizeof(path), "%s/class/net/%s/%s", SYSFS_ROOT, iface, field);
    if (n < 0 || (size_t)n >= sizeof(path)) return ENAMETOOLONG;
    FILE *fp = fopen(path, "r");
    if (!fp) return errno;
    errno = 0;
    size_t len = fread(buf, 1, size - 1, fp);
    int error = ferror(fp) ? (errno ? errno : EIO) : 0;
    if (len == size - 1) error = EOVERFLOW;
    fclose(fp);
    if (error) return error;
    while (len && isspace((unsigned char)buf[len - 1])) len--;
    if (!len || memchr(buf, '\0', len)) return EINVAL;
    buf[len] = '\0';
    return 0;
}

static int uint_value(const char *s, unsigned long long *value)
{
    if (!s || !*s) return EINVAL;
    for (const char *p = s; *p; p++) if (*p < '0' || *p > '9') return EINVAL;
    errno = 0;
    char *end;
    *value = strtoull(s, &end, 10);
    return errno == ERANGE ? ERANGE : *end ? EINVAL : 0;
}

static void emit(const char *ibdev)
{
    char iface[256] = {0}, timestamp[64], text[128];
    int mapping = find_iface(ibdev, iface, sizeof(iface));
    int errors[8] = {0};
    const char *fields[8] = {"operstate", "carrier", "rx_packets", "tx_packets", "rx_bytes", "tx_bytes", "rx_errors", "tx_errors"};
    time_t now = time(NULL);
    struct tm utc;
    if (!gmtime_r(&now, &utc) || !strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc)) {
        fputs("Cannot obtain timestamp\n", stderr); exit(1);
    }
    fputs("{\"schema_version\":\"bluefield-monitor-review-1\",\"source\":\"bluefield\",\"measurement_scope\":\"host_interface_counters\",\"timestamp\":", stdout);
    string_json(timestamp);
    fputs(",\"ibdev\":", stdout); string_json(ibdev);
    fputs(",\"interface\":", stdout); string_json(mapping ? NULL : iface);
    for (int i = 0; i < 8; i++) {
        char field[128];
        if (i < 2) snprintf(field, sizeof(field), "%s", fields[i]);
        else snprintf(field, sizeof(field), "statistics/%s", counters[i - 2]);
        errors[i] = mapping ? mapping : read_text(iface, field, text, sizeof(text));
        unsigned long long value = 0;
        if (!errors[i] && i > 0) errors[i] = uint_value(text, &value);
        if (!errors[i] && i == 1 && value > 1) errors[i] = EINVAL;
        putchar(','); string_json(fields[i]); putchar(':');
        if (errors[i]) fputs("null", stdout);
        else if (i == 0) string_json(text);
        else printf("%llu", value);
    }
    fputs(",\"read_errors\":{", stdout);
    int count = 0;
    if (mapping) {
        fputs("\"interface\":", stdout);
        string_json(mapping == EEXIST ? "ambiguous_interface_mapping" : strerror(mapping)); count++;
    }
    for (int i = 0; i < 8; i++) if (errors[i]) {
        if (count++) putchar(',');
        string_json(fields[i]); putchar(':'); string_json(strerror(errors[i]));
    }
    fputs("}}\n", stdout);
}

int main(int argc, char **argv)
{
    unsigned long long samples = 3;
    if (argc == 2 && !strcmp(argv[1], "--help")) {
        puts("Usage: bluefield_monitor [--samples 1..100] (default 3; interval 2 seconds; stdout only)"); return 0;
    }
    if (argc != 1 && (argc != 3 || strcmp(argv[1], "--samples") || uint_value(argv[2], &samples) || samples < 1 || samples > 100)) {
        fputs("Expected --samples 1..100\n", stderr); return 2;
    }
    struct doca_devinfo **list = NULL;
    uint32_t devices = 0;
    doca_error_t result = doca_devinfo_create_list(&list, &devices);
    if (result != DOCA_SUCCESS) { fprintf(stderr, "DOCA enumeration failed: %s\n", doca_error_get_descr(result)); return 1; }
    fprintf(stderr, "DOCA devices: %u; bounded samples: %llu; stdout only\n", devices, samples);
    if (!devices) { doca_devinfo_destroy_list(list); return 1; }
    int failed = 0;
    for (unsigned long long sample = 0; sample < samples; sample++) {
        for (uint32_t i = 0; i < devices; i++) {
            char ibdev[256] = {0};
            result = doca_devinfo_get_ibdev_name(list[i], ibdev, sizeof(ibdev));
            if (result != DOCA_SUCCESS) { fprintf(stderr, "Device %u IB name unavailable: %s\n", i, doca_error_get_descr(result)); failed = 1; continue; }
            emit(ibdev);
        }
        if (fflush(stdout) == EOF) { failed = 1; break; }
        if (sample + 1 < samples) sleep(2);
    }
    doca_devinfo_destroy_list(list);
    return failed ? 1 : 0;
}
