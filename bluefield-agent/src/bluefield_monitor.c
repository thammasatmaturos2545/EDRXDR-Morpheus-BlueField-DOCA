#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <time.h>

#include <doca_dev.h>
#include <doca_error.h>

#define PATH_SIZE 512
#define NAME_SIZE 128


static int get_iface_from_ibdev(
    const char *ibdev,
    char *iface,
    size_t iface_size)
{
    char path[PATH_SIZE];

    snprintf(
        path,
        sizeof(path),
        "/sys/class/infiniband/%s/device/net",
        ibdev
    );

    DIR *dir = opendir(path);

    if (dir == NULL)
        return -1;

    struct dirent *entry;

    while ((entry = readdir(dir)) != NULL) {

        if (
            strcmp(entry->d_name, ".") != 0 &&
            strcmp(entry->d_name, "..") != 0
        ) {

            snprintf(
                iface,
                iface_size,
                "%s",
                entry->d_name
            );

            closedir(dir);
            return 0;
        }
    }

    closedir(dir);

    return -1;
}


static unsigned long long read_counter(
    const char *iface,
    const char *counter)
{
    char path[PATH_SIZE];

    snprintf(
        path,
        sizeof(path),
        "/sys/class/net/%s/statistics/%s",
        iface,
        counter
    );

    FILE *fp = fopen(path, "r");

    if (fp == NULL)
        return 0;

    unsigned long long value = 0;

    fscanf(fp, "%llu", &value);

    fclose(fp);

    return value;
}


static void print_timestamp(char *buffer, size_t size)
{
    time_t now = time(NULL);

    struct tm tm_info;

    gmtime_r(
        &now,
        &tm_info
    );

    strftime(
        buffer,
        size,
        "%Y-%m-%dT%H:%M:%SZ",
        &tm_info
    );
}


int main(void)
{
    struct doca_devinfo **dev_list = NULL;

    uint32_t nb_devs = 0;

    doca_error_t result;


    result = doca_devinfo_create_list(
        &dev_list,
        &nb_devs
    );


    if (result != DOCA_SUCCESS) {

        fprintf(
            stderr,
            "Failed to enumerate DOCA devices: %s\n",
            doca_error_get_descr(result)
        );

        return 1;
    }


    fprintf(
        stderr,
        "EDRXDR BlueField Monitor started\n"
    );

    fprintf(
        stderr,
        "DOCA devices: %u\n",
        nb_devs
    );


    while (1) {

        for (uint32_t i = 0; i < nb_devs; i++) {

            char ibdev[NAME_SIZE] = {0};
            char iface[NAME_SIZE] = {0};
            char timestamp[64] = {0};


            result = doca_devinfo_get_ibdev_name(
                dev_list[i],
                ibdev,
                sizeof(ibdev)
            );


            if (result != DOCA_SUCCESS)
                continue;


            if (
                get_iface_from_ibdev(
                    ibdev,
                    iface,
                    sizeof(iface)
                ) != 0
            ) {

                snprintf(
                    iface,
                    sizeof(iface),
                    "unknown"
                );
            }


            unsigned long long rx_packets =
                read_counter(
                    iface,
                    "rx_packets"
                );

            unsigned long long tx_packets =
                read_counter(
                    iface,
                    "tx_packets"
                );

            unsigned long long rx_bytes =
                read_counter(
                    iface,
                    "rx_bytes"
                );

            unsigned long long tx_bytes =
                read_counter(
                    iface,
                    "tx_bytes"
                );

            unsigned long long rx_errors =
                read_counter(
                    iface,
                    "rx_errors"
                );

            unsigned long long tx_errors =
                read_counter(
                    iface,
                    "tx_errors"
                );


            print_timestamp(
                timestamp,
                sizeof(timestamp)
            );


            printf(
                "{"
                "\"timestamp\":\"%s\","
                "\"source\":\"bluefield\","
                "\"ibdev\":\"%s\","
                "\"interface\":\"%s\","
                "\"rx_packets\":%llu,"
                "\"tx_packets\":%llu,"
                "\"rx_bytes\":%llu,"
                "\"tx_bytes\":%llu,"
                "\"rx_errors\":%llu,"
                "\"tx_errors\":%llu"
                "}\n",

                timestamp,
                ibdev,
                iface,
                rx_packets,
                tx_packets,
                rx_bytes,
                tx_bytes,
                rx_errors,
                tx_errors
            );


            fflush(stdout);
        }


        sleep(2);
    }


    doca_devinfo_destroy_list(
        dev_list
    );

    return 0;
}
